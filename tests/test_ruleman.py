import pytest
from ruleman import *

def test_rulevar():
    # unit tests for RuleVar
    # RuleVar is a class that represents a variable in a rule.

    a = RuleVar(1)
    b = RuleVar('asdf')
    c = RuleVar([1,2,3])
    d = RuleVar(2)
    e = RuleVar('fdsa')
    r1 = a + d
    r2 = b + e
    r3 = c + [4,5,6]
    r4 = c + d
    r5 = a + c

    assert a.vartype == 'VARIABLE'
    assert b.vartype == 'VARIABLE'
    assert c.vartype == 'GROUP'
    assert d.vartype == 'VARIABLE'
    assert e.vartype == 'VARIABLE'
    assert r1.vartype == 'VARIABLE'
    assert r2.vartype == 'VARIABLE'
    assert r3.vartype == 'GROUP'
    assert r4.vartype == 'GROUP'
    assert r5.vartype == 'GROUP'
    
    assert str(r1) == '3'
    assert str(r2) == 'asdffdsa'
    assert str(r3) == '[1, 2, 3, 4, 5, 6]'
    assert str(r4) == '[1, 2, 3, 2]'
    assert str(r5) == '[1, 1, 2, 3]'
    
    
def test_vars():
    assert checkVariableIsSet('a') == False
    setVariable('a', 1)
    assert checkVariableIsSet('a') == True
    assert getVariable('a') == 1
    assert checkVariableValue('a', 1) == True
    assert checkVariableValue('a', 2) == False
    setVariable('b', 'asdf')
    assert checkVariableIsSet('b') == True
    assert checkVariableValue('b', 'asdf') == True
    assert checkVariableValue('b', 'fdsa') == False
    
    
def test_rulevar_eq():
    a = RuleVar(1)
    b = RuleVar([1,2,3])
    c = RuleVar(2)
    d = RuleVar([1,2,3])
    e = RuleVar([1,2,4])
    f = RuleVar('asdf')
    
    assert a == 1
    assert a == a
    assert a != c
    assert b == [1,2,3]
    assert b == b
    assert b == d
    assert b != e
    assert b != f
    assert (1 <= RuleVar(2) <= 3) == True
    assert (1 <= RuleVar(1) <= 3) == True
    assert (1 <= RuleVar(3) <= 3) == True
    assert (1 <= RuleVar(0) <= 1) == False
    assert (1 <= RuleVar(4) <= 3) == False

def test_rulevar_add():
    a = RuleVar(1)
    b = RuleVar([1,2,3])
    c = RuleVar(2)
    d = RuleVar([1,2,3])
    e = RuleVar([1,2,4])
    f = RuleVar('asdf')
    
    assert a + c == 3
    assert a + 2 == 3
    assert a + '2' == '12'
    assert b + d == [1,2,3,1,2,3]
    assert b + [1,2,4] == [1,2,3,1,2,4]
    assert b + 'asdf' == [1,2,3,'asdf']
    assert c + 3 == 5
    assert c + '3' == '23'
    assert f + 'fdsa' == 'asdffdsa'
    
def test_words() -> None:
    startRule('CREATE GROUP TEST')
    assert nextWordIs('CREATE') == True
    assert nextWordIs('GROUP') == False
    assert nextWord() == 'CREATE'
    assert nextWord() == 'GROUP'
    assert nextWord() == 'TEST'
    assert nextWord() == ''
    
def test_nextWordIs():
    startRule('CREATE GROUP TEST')
    assert nextWordIs('CREATE') == True
    assert nextWordIs('GROUP') == False
    assert nextWordIs('TEST') == False
    assert nextWordIs('') == False
    assert nextWordIs(['CREATE', 'DESTROY']) == True
    assert nextWordIs(['DESTROY', 'CREATE']) == True
    assert nextWordIs(['DESTROY', 'fdsa']) == False
    nextWord()
    assert nextWordIs('GROUP') == True
    nextWord()
    assert nextWordIs('TEST') == True
    assert nextWordIs(['fdsa', '']) == False
    nextWord()
    assert nextWordIs('') == True
    assert nextWordIs('fdsa') == False
    assert nextWordIs(['fdsa', '']) == True
    assert nextWordIs(['fdsa', 'asdf']) == False
    
def test_getValue():
    setVariable('A', 5)
    startRule('1 TRUE 2 FALSE TIME A')
    assert getValue() == 1
    assert getValue() == True
    assert getValue() == 2
    assert getValue() == False
    assert type(getValue()) == int
    assert getValue() == 5
    
def test_condition():
    setVariable('A', 1)
    setVariable('B', 2)
    setVariable('C', 'asdf')
    setVariable('D', 'fdsa')
    startRule('A IS 1')
    assert type(checkCondition()) == bool
    startRule('A IS 1')
    assert checkCondition() == True
    startRule('B IS NOT 1')
    assert checkCondition() == True
    startRule('A IS 1')
    assert ifStatement() == True
    startRule('A IS 1 AND B IS NOT 1')
    assert ifStatement() == True
    startRule('A IS BETWEEN 0 AND 2')
    assert ifStatement() == True
    startRule('A IS BETWEEN 0 AND 1')
    assert ifStatement() == True
    startRule('A IS BETWEEN 1 AND 2')
    assert ifStatement() == True
    startRule('A IS BETWEEN 2 AND 3')
    assert ifStatement() == False
    startRule('A IS BETWEEN 0 AND 0')
    assert ifStatement() == False
    startRule('A IS BETWEEN 2 AND 1')
    assert ifStatement() == False
    startRule('A IS BETWEEN 0 AND 1 OR B IS 2')
    assert ifStatement() == True
    startRule('A IS BETWEEN 0 AND 1 OR B IS 3')
    assert ifStatement() == True
    startRule('A IS 1 AND B IS 2 AND C IS asdf AND D IS fdsa')
    assert ifStatement() == True
    startRule('C IS asdf OR D IS fdsa')
    assert ifStatement() == True
    startRule('A IS 5')
    assert ifStatement() == False
    startRule('B IS 2')
    assert ifStatement() == True
    startRule('A IS BETWEEN 4 AND 5 OR B IS 3')
    assert ifStatement() == False
    startRule('C IS asdf OR D IS fdsa')
    assert ifStatement() == True
    startRule('C IS fdsa OR D IS fdsa')
    assert ifStatement() == True
    startRule('A IS 5 OR B IS 2')
    assert ifStatement() == True
    startRule('A IS BETWEEN 4 AND 5 OR B IS 2')
    assert ifStatement() == True

def test_addStatement():
    setVariable('TEST', 1)
    startRule('1 TO TEST')
    addStatement()
    assert getVariable('TEST') == 2
    startRule('1 TO TEST')
    addStatement()
    assert getVariable('TEST') == 3
    
def test_processCommand():
    processCommand('CREATE GROUP TEST')
    assert checkVariableIsSet('TEST') == True
    assert checkVariableValue('TEST', []) == True
    processCommand('SET A TO TRUE')
    assert checkVariableIsSet('A') == True
    assert checkVariableValue('A', True) == True
    processCommand('SET B TO 1')
    assert checkVariableIsSet('B') == True
    assert checkVariableValue('B', 1) == True
    processCommand('SET C TO asdf')
    assert checkVariableIsSet('C') == True
    assert checkVariableValue('C', 'asdf') == True

def test_logStatement(capfd):
    processCommand('LOG TEXT HELLO WORLD')
    out, err = capfd.readouterr()
    assert out == 'HELLO WORLD\n'
    processCommand('SET A TO TEST')
    processCommand('LOG VALUE A')
    out, err = capfd.readouterr()
    assert out == 'TEST\n' 
    
def test_groups():
    processCommand('CREATE GROUP TEST')
    assert checkVariableIsSet('TEST') == True
    assert checkVariableValue('TEST', []) == True
    assert type(variables['TEST']) == RuleVar
    processCommand('SET ABC TO TRUE')
    processCommand('ADD ABC TO TEST')
    assert checkVariableValue('TEST', [True]) == True
    
def test_setStatement():
    processCommand('SET AB TO 1 AND BC TO 2')
    assert checkVariableValue('AB', 1) == True
    assert checkVariableValue('BC', 2) == True
    processCommand('IF AB IS 1 THEN SET AB TO 2 AND BC TO 3')
    assert checkVariableValue('AB', 2) == True
    assert checkVariableValue('BC', 3) == True
    
def test_function():
    processCommand('START FUNCTION TEST; SET A TO 1; END FUNCTION')
    assert checkVariableIsSet('TEST') == True
    assert checkVariableValue('TEST', ['SET A TO 1']) == True
    