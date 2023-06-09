# Light manager that connect sensors and lights.
# Uses a ruleset to determine when to turn on/off lights.

from functools import total_ordering
from math import e
from multiprocessing import Value
from sched import scheduler
import time
from typing import Any, Union
import re

import lifx
from presence import getPresence, sensorVariable
from apscheduler.schedulers.background import BackgroundScheduler

functionName = None
inComment = False

dataTypes = ['SWITCH', 'NUMBER', 'DECIMAL', 'TEXT']
dataClasses = ['INPUT', 'OUTPUT', 'VARIABLE']
pluralClasses = ['INPUTS', 'OUTPUTS', 'VARIABLES']

class RuleSyntaxError(ValueError):
    pass

@total_ordering
class RuleVar:
    def __init__(self, value=None, vartype=''):
        self.props = {}
        if vartype == '':
            if type(value) == list:
                self.vartype = 'GROUP'
            else:
                self.vartype = 'VARIABLE'
        else:
            self.vartype = vartype

        if self.vartype == 'GROUP':
            if type(value) == list:
                self.items = value
            elif value == None:
                self.items = []
            else:
                self.items = [value]
        else:
            self.value = value
    def get(self, property):
        property = property.upper()
        if property == 'GROUP':
            return self.props['VARTYPE'] == 'GROUP' 
        elif property == 'NAME':
            for var in variables:
                if variables[var] == self:
                    return var
        elif property == 'VALUE':
            if self.props['VARTYPE'] == 'GROUP':
                return self.props['ITEMS']
            else:
                return self.props['VALUE']
        else:
            return self.props[property]
        
    def set(self, property, value):
        property = property.upper()
        if property == 'GROUP':
            if value:
                self.props['VARTYPE'] = 'GROUP'
            else:
                self.props['VARTYPE'] = 'VARIABLE'
        elif property == 'NAME':
            for var in variables:
                if variables[var] == self:
                    variables[value] = self
                    del variables[var]
        elif property == 'VALUE':
            if self.props['VARTYPE'] == 'GROUP':
                for item in self.props['ITEMS']:
                    if type(item) == RuleVar:
                        item.set('VALUE', value)
            else:
                self.props['VALUE'] = value
    
        else:
            self.props[property] = value
            
    def __getattr__(self, name: str):
        #print('Getting', name)
        if name == 'props':
            return super().__getattribute__('PROPS')
        else:
            return self.get(name)
    
    def __setattr__(self, name: str, value: Any) -> None:
        #print('Setting', name, 'to', value)
        if name == 'props':
            super().__setattr__('PROPS', value)
        else:
            self.set(name, value)


    def __repr__(self):
        if self.vartype == 'GROUP':
            return f'<RuleVar GROUP: {self.items}>'
        else:
            return f'<RuleVar: {self.value}>'
    def __str__(self):
        if self.vartype == 'GROUP':
            return f'(RULEVAR GROUP: {self.items})'
        else:
            return f'(RULEVAR: {self.value})' 
    def __iter__(self):
        self.iterNum = -1
        return self
    def __next__(self):
        self.iterNum += 1
        if self.vartype == 'GROUP':
            if self.iterNum < len(self.items):
                return self.items[self.iterNum]
            else:
                raise StopIteration
        else:
            if self.iterNum == 0:
                return self.value
            else:
                raise StopIteration
            
    def __add__(self, other):
        if self.vartype == 'GROUP':
            if type(other) == list:
                return RuleVar(self.items + other)
            elif type(other) == RuleVar:
                if other.vartype == 'GROUP':
                    return RuleVar(self.items + other.items)
                else:
                    return RuleVar(self.items + [other.value])
            else:
                return RuleVar(self.items + [other])
        else:
            if type(other) == list:
                self.vartype = 'GROUP'
                return RuleVar([self.value] + other)
            elif type(other) == RuleVar:
                if other.vartype == 'GROUP':
                    return RuleVar([self.value] + other.items)
                else:
                    return RuleVar(self.value + other.value)
            elif type(other) == str:
                if type(self.value) == str:
                    return RuleVar(self.value + other)
                else:
                    return RuleVar(str(self.value) + other)
            return RuleVar(self.value + other)
                
    def __iadd__(self, other) -> None:
        if self.vartype == 'GROUP':
            if type(other) == list:
                self.items += other
            elif type(other) == RuleVar:
                if other.vartype == 'GROUP':
                    self.items += other.items
                else:
                    self.items += [other]
            else:
                self.items += [other]
        else:
            if type(other) == list:
                self.vartype = 'GROUP'
                self.items = [self.value] + other
            elif type(other) == RuleVar:
                if other.vartype == 'GROUP':
                    self.items = [self.copy()] + other.items
                    self.vartype = 'GROUP'
                else:
                    self.value += other.value
            elif type(other) == str:
                if type(self.value) == str:
                    self.value += other
                else:
                    self.value = str(self.value) + other
            else:
                self.value += other
        return self

    def __eq__(self, other):
        if self.vartype == 'GROUP':
            if type(other) == list:
                return self.items == other
            elif type(other) == RuleVar:
                if other.vartype == 'GROUP':
                    return self.items == other.items
                else:
                    return False
            else:
                return False
        else:
            if type(other) == list:
                return False
            elif type(other) == RuleVar:
                if other.vartype == 'GROUP':
                    return False
                else:
                    return self.value == other.value
            else:
                return self.value == other
            
    def __lt__(self, other):
        if self.vartype == 'GROUP':
            if type(other) == list:
                return self.items < other
            elif type(other) == RuleVar:
                if other.vartype == 'GROUP':
                    return self.items < other.items
                else:
                    return False
            else:
                return False
        else:
            if type(other) == list:
                return False
            elif type(other) == RuleVar:
                if other.vartype == 'GROUP':
                    return False
                else:
                    return self.value < other.value
            else:
                return self.value < other
            
scheduler = None
variables = {}
rules = [
    'SET BL TO BS1',
    'SET KL TO KS1',
    'SET LRL TO LRS1',
    'IF AUTO IS TRUE AND TIME IS BETWEEN 20:30 AND 24:00 OR TIME IS BETWEEN 00:00 AND 03:00 THEN SET BRIGHTNESS TO 0.5 AND KELVIN TO 1800',
    'IF AUTO IS TRUE AND TIME IS BETWEEN 03:00 AND 04:30 OR TIME IS BETWEEN 19:00 AND 23:00 THEN SET BRIGHTNESS TO 0.8 AND KELVIN TO 3000',
    'IF AUTO IS TRUE AND TIME IS BETWEEN 04:30 AND 19:00 THEN SET BRIGHTNESS TO 1 AND KELVIN TO 5000',
    'IF SLEEP IS SET THEN TURN OFF LAMPS',
    'IF HOME IS NOT SET THEN TURN OFF LAMPS',
]

def checkVariableIsSet(variable: str) -> bool:
    # Check if a variable is set.
    if variable in variables:
        return True
    return False

def checkVariableValue(variable: str, value: str) -> bool:
    # Check if a variable has a specific value.
    if variable in variables:
        if variables[variable] == value:
            return True
    return False

def getVariable(variable: str) -> RuleVar:
    # Get a variable.
    if variable in variables:
        return variables[variable]
    return RuleVar()

def setVariable(variable: str, value: Any) -> None:
    # Set a variable.
    if variable in variables:
        variables[variable].set('value', value)
    elif type(value) == RuleVar:
        variables[variable] = value
    else:
        variables[variable] = RuleVar(value)
         
#python 3.9 compatibility
def exportVariable(variable: Union[str, RuleVar]) -> Any:
#def exportVariable(variable: str | RuleVar) -> Any:
    # Grabs an internal variable and strips the RuleVar wrapper.
    if type(variable) == str:
        rv = getVariable(variable)
    else:
        rv = variable
    if rv.vartype == 'GROUP':
        newList = []
        for item in rv.items:
            if type(item) == RuleVar:
                newList.append(exportVariable(item))
            else:
                newList.append(item)
        return newList
    else:
        if type(rv.value) == RuleVar:
            return exportVariable(rv.value)
        else:
            return rv.value

def checkVariableBetween(variable: str, value1: int, value2: int) -> bool:
    # Check if a variable is between two values.
    if variable in variables:
        if variables[variable] >= value1 and variables[variable] <= value2:
            return True
    return False

def startRule(rule: str):
    global ruleWords
    global currentRule
    currentRule = rule
    ruleWords = rule.split(' ')
    
def nextWord() -> str:
    global ruleWords
    if len(ruleWords) > 0:
        return ruleWords.pop(0)
    return ''

def nextWordIs(word: Union[str, list]) -> bool:
#def nextWordIs(word: str|list) -> bool:
    global ruleWords
    if len(ruleWords) > 0:
        if type(word) == list:
            if ruleWords[0] in word:
                return True
        else:
            if ruleWords[0] == word:
                return True
    else:
        if type(word) == list:
            if '' in word:
                return True
        else:
            if word == '':
                return True
    return False

def getValue(word=None) -> Any:
    if word == None:
        value = nextWord()
    else:
        value = word
    if value == 'TRUE':
        return True
    elif value == 'FALSE':
        return False
    elif value.isnumeric():
        return int(value)
    elif re.match('[0-9]+:[0-9]+', value):
        return int(value.replace(':', ''))
    elif re.match('[0-9]+\\.[0-9]+', value):
        return float(value)
    elif value == 'TIME':
        return int(time.strftime('%H%M'))
    elif checkVariableIsSet(value):
        return getVariable(value)
    else:
        return value
    
def getNumericValue(word=None) -> int:
    value = getValue(word)
    if type(value) == int:
        return value
    else:
        raise RuleSyntaxError('Expected numeric value', value)
    
def getVariableValue(word=None) -> RuleVar:
    if word == None:
        variable = nextWord()
    else:
        variable = word
    if checkVariableIsSet(variable):
        return getVariable(variable)
    else:
        raise RuleSyntaxError('Variable not set', variable)
    
def getNamedVariableValue(word=None) -> RuleVar:
    if word == None:
        name = nextWord()
    else:
        name = word
    if checkVariableIsSet(name):
        return getVariable(name), name
    else:
        raise RuleSyntaxError('Variable not set', name)
    
def checkCondition(checkVal=None) -> bool:
    if checkVal is None:
        checkVal = getValue()
        if nextWord() != 'IS':
            raise RuleSyntaxError('Expected IS')
    operation = getValue()
    if operation == 'NOT':
        return not checkCondition(checkVal)
    if operation == 'SET':
        return checkVal == True
    elif operation == 'BETWEEN':
        value1 = getNumericValue()
        if nextWord() != 'AND':
            raise RuleSyntaxError('Expected AND')
        value2 = getNumericValue()
        return value1 <= checkVal <= value2
    else:
        value = operation
        return checkVal == value

def ifStatement() -> bool:
    result = checkCondition()
    while not nextWordIs(['THEN', '']):
        logicWord = nextWord()
        if logicWord == 'AND':
            result = result and checkCondition()
        elif logicWord == 'OR':
            # The arguments need to be consumed, but are discard if the first part was true.
            if result:
                checkCondition()
            else:
                result = result or checkCondition()
        else:
            raise RuleSyntaxError(f'Expected AND or OR, got {logicWord}')
    return result

def setStatement() -> None:
    name = nextWord()
    if nextWord() != 'TO':
        raise RuleSyntaxError('Expected TO')
    value = getValue()
    setVariable(name, value)
    if nextWordIs('AND'):
        nextWord()
        setStatement()

def createStatement() -> None:
    newType = nextWord()
    if newType == 'GROUP':
        newGroup = nextWord()
        setVariable(newGroup, RuleVar(vartype='GROUP'))
    else:
        raise RuleSyntaxError('Expected GROUP')
    
def getList():
    items = []
    while True:
        items += [nextWord()]
        if nextWordIs('AND'):
            nextWord()
        else:
            break
    return items

def addStatement() -> None:
    items = getList()
    if nextWord() != 'TO':
        raise RuleSyntaxError('Expected TO')
    var,name = getNamedVariableValue()
    if var.vartype == 'GROUP':
        var += [getVariableValue(item) for item in items]
    else:
        var += sum([getValue(item) for item in items])
    #setVariable(name, var)
    
def defineStatement() -> None:
    items = getList()
    if nextWord() != 'AS':
        dataType = 'ANY'
        dataClass = 'ANY'
    else:
        dataType = nextWord()
        dataClass = nextWord()
        if dataClass == '':
            dataClass = 'ANY'
    for item in items:
        if not checkVariableIsSet(item):
            var = RuleVar()
        else :
            var = getVariable(item)
        var.targetType = dataType
        var.targetClass = dataClass
        
def expectStatement() -> None:
    items = getList()
    if nextWord() != 'AS':
        dataType = 'ANY'
        dataClass = 'ANY'
    else:
        dataType = nextWord()
        dataClass = nextWord()
        if dataClass == '':
            dataClass = 'ANY'
    for item in items:
        if not checkVariableIsSet(item):
            raise RuleSyntaxError('Variable not set', item)
        var = getVariable(item)
        var.targetType = dataType
        var.targetClass = dataClass

def toggleStatement() -> None:
    items = getList()
    for item in items:
        if item in variables:
            variables[item] = not variables[item]
        else:
            raise RuleSyntaxError('Unknown item: ' + item)
        
def turnStatement() -> None:
    state = nextWord()
    if state == 'ON':
        setTo = True
    elif state == 'OFF':
        setTo = False
    else:
        raise RuleSyntaxError('Expected ON or OFF')
    items = getList()
    for item in items:
        setVariable(item, setTo)

def addLightVariables():
    for light in lifx.props['lightPower']:
        setVariable(light.upper(), lifx.props['lightPower'][light])
    print(variables)
    setVariable('KELVIN', lifx.props['kelvin'])
    setVariable('BRIGHTNESS', lifx.props['brightness'])
    allLamps = RuleVar(vartype='GROUP')
    setVariable('LAMPS', allLamps)
    allLamps += [getVariableValue(light.upper()) for light in lifx.props['lightPower']]

    
def logStatement() -> None:
    logType = nextWord()
    if logType == 'TEXT':
        print(' '.join(ruleWords))
    elif logType == 'VALUE':
        value = getValue()
        print(value)
    
def startBlockCommand() -> None:
    global inComment, functionName
    blockType = nextWord()
    if blockType == 'NOTE':
        inComment = True
    elif blockType == 'FUNCTION':
        functionName = nextWord()
        newVar = RuleVar(vartype='GROUP')
        newVar.set('runable', True)
        setVariable(functionName, newVar)
    else:
        raise RuleSyntaxError('Expected NOTE or FUNCTION')
    
def endBlockCommand() -> None:
    global inComment, functionName
    blockType = nextWord()
    if blockType == 'NOTE':
        inComment = False
    elif blockType == 'FUNCTION':
        functionName = None
    else:
        raise RuleSyntaxError('Expected NOTE or FUNCTION')
    
def processCommand(statement: str=None) -> None:
    try:
        if statement != None:
            startRule(statement)
        command = nextWord()
        if len(command) == 0:
            return
        if command == 'END':
            endBlockCommand()
        elif functionName != None:
            variable = getVariable(functionName)
            variable += statement
        elif inComment:
            return
        elif command == 'IF':
            if ifStatement():
                nextWord()
                processCommand()
        elif command == 'SET':
            setStatement()
        elif command == 'CREATE':
            createStatement()
        elif command == 'ADD':
            addStatement()
        elif command == 'TOGGLE':
            toggleStatement()
        elif command == 'TURN':
            turnStatement()
        elif command == 'LOG':
            logStatement()
        elif command == 'NOTE':
            return
        elif command == 'DEFINE':
            defineStatement()
        elif command == 'EXPECT':
            expectStatement()
        elif command == 'START':
            startBlockCommand()
        elif checkVariableIsSet(command):
            run(getVariableValue(command))
        else:
            raise RuleSyntaxError('Unknown command: ' + command)
    except RuleSyntaxError as e:
        print(f'Syntax Error: {e.args}')

def updateLights():
    newData = {'mode': {'brightness': exportVariable('BRIGHTNESS'), 'kelvin': exportVariable('KELVIN')}}
    newData['bulbs'] = []
    for light in lifx.props['lightPower']:
        newData['bulbs'] += [{'name': light, 'state': exportVariable(light.upper())}]
    lifx.readData(newData)

def updateActiveVariables():
    for sensor in sensorVariable:
        setVariable(sensorVariable[sensor]['var'].upper(), getPresence(sensor))
    

def checkRules():
    updateActiveVariables()
    if checkVariableIsSet('ENVIRONMENT'):
        for cmd in getVariable('ENVIRONMENT').value:
            processCommand(cmd)
    updateLights()
        
def run(rules: Union[list, str]) -> None:
    if type(rules) == str:
        runList = rules.split(';')
    elif type(rules) == list:
        runList = rules
    elif type(rules) == RuleVar:
        runList = rules.value
    for rule in runList:
        print(rule)
        rule = rule.strip()
        #print(variables) # debug
        processCommand(rule)
    # Check if this affected the state of the system.
    checkRules()

def runFunction(name: str) -> None:

    run(getVariableValue(name))

def addSensorVariables():
    for sensor in sensorVariable.values():
        setVariable(sensor['var'], False)
        
def loadRuleFile(filename: str) -> list:
    try:
        with open(f'ruleman/{filename}.rules', 'r') as f:
            print(f'Loading {filename}.rules')
            return f.read().splitlines()
    except FileNotFoundError:
        return ''
    
def runRuleFile(filename: str) -> None:
    run(loadRuleFile(filename))

def init():
    global scheduler, rules
    addLightVariables()
    addSensorVariables()
    runRuleFile('init')
    runRuleFile('env')
    # Start the scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(checkRules, 'interval', seconds=10)
    scheduler.start()
