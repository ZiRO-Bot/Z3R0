import operator
import re
import sys

from pyparsing import (
    CaselessLiteral,
    Combine,
    Forward,
    Literal,
    Optional,
    ParseException,
    StringEnd,
    Word,
    ZeroOrMore,
    alphanums,
    alphas,
    nums,
)


# ----------------------------------------------------------------------------
# Variables that hold intermediate parsing results and a couple of
# helper functions.
exprStack = []  # Holds operators and operands parsed from input.
targetvar = None  # Holds variable name to left of '=' sign in LA equation.


def _pushFirst(str, loc, toks):
    print("pushing ", toks[0], "str is ", str)
    exprStack.append(toks[0])


def _assignVar(str, loc, toks):
    global targetvar
    targetvar = toks[0]


# -----------------------------------------------------------------------------
# The following statements define the grammar for the parser.

point = Literal(".")
e = CaselessLiteral("E")
plusorminus = Literal("+") | Literal("-")
number = Word(nums)
integer = Combine(Optional(plusorminus) + number)
floatnumber = Combine(integer + Optional(point + Optional(number)) + Optional(e + integer))

lbracket = Literal("[")
rbracket = Literal("]")
ident = Forward()
## The definition below treats array accesses as identifiers. This means your expressions
## can include references to array elements, rows and columns, e.g., a = b[i] + 5.
## Expressions within []'s are not presently supported, so a = b[i+1] will raise
## a ParseException.
ident = Combine(
    Word(alphas + "-", alphanums + "_") + ZeroOrMore(lbracket + (Word(alphas + "-", alphanums + "_") | integer) + rbracket)
)

plus = Literal("+")
minus = Literal("-")
mult = Literal("*")
div = Literal("/")
lpar = Literal("(").suppress()
rpar = Literal(")").suppress()
addop = plus | minus
multop = mult | div
expop = Literal("^")
assignop = Literal("=")

expr = Forward()
atom = (e | floatnumber | integer | ident).setParseAction(_pushFirst) | (lpar + expr.suppress() + rpar)
factor = Forward()
factor << atom + ZeroOrMore((expop + factor).setParseAction(_pushFirst))

term = factor + ZeroOrMore((multop + factor).setParseAction(_pushFirst))
expr << term + ZeroOrMore((addop + term).setParseAction(_pushFirst))
equation = (ident + assignop).setParseAction(_assignVar) + expr + StringEnd()

# End of grammar definition
# -----------------------------------------------------------------------------
## The following are helper variables and functions used by the Binary Infix Operator
## Functions described below.


## We don't support unary negation for vectors and matrices
class UnaryUnsupportedError(Exception):
    pass


## Binary infix operator (BIO) functions.  These are called when the stack evaluator
## pops a binary operator like '+' or '*".  The stack evaluator pops the two operand, a and b,
## and calls the function that is mapped to the operator with a and b as arguments.  Thus,
## 'x + y' yields a call to addfunc(x,y). Each of the BIO functions checks the prefixes of its
## arguments to determine whether the operand is scalar, vector, or matrix.  This information
## is used to generate appropriate C code.  For scalars, this is essentially the input string, e.g.
## 'a + b*5' as input yields 'a + b*5' as output.  For vectors and matrices, the input is translated to
## nested function calls, e.g. "V3_a + V3_b*5"  yields "V3_vAdd(a,vScale(b,5)".  Note that prefixes are
## stripped from operands and function names within the argument list to the outer function and
## the appropriate prefix is placed on the outer function for removal later as the stack evaluation
## recurses toward the final assignment statement.


def _assignfunc(a, b):
    ## The '=' operator is used for assignment
    return "%s=%s" % (a, b)


## End of BIO func definitions
##----------------------------------------------------------------------------

# Map  operator symbols to corresponding BIO funcs
opn = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "^": operator.pow,
    # "**": operator.pow,
}


##----------------------------------------------------------------------------
# Recursive function that evaluates the expression stack
def _evaluateStack(s):
    op = s.pop()
    if op in "+-*/^":
        op2 = _evaluateStack(s)
        op1 = _evaluateStack(s)
        result = opn[op](int(op1), int(op2))
        # if debug_flag:
        #    print(result)
        print(result)
        return result
    else:
        return op


##----------------------------------------------------------------------------
# The parse function that invokes all of the above.
def parse(input_string):
    """
    Accepts an input string containing an LA equation, e.g.,
    "M3_mymatrix = M3_anothermatrix^-1" returns C code function
    calls that implement the expression.
    """

    global exprStack
    global targetvar

    # Start with a blank exprStack and a blank targetvar
    exprStack = []
    targetvar = None

    if input_string != "":
        # try parsing the input string
        try:
            L = equation.parseString(input_string)
        except ParseException as err:
            print("Parse Failure", file=sys.stderr)
            print(err.line, file=sys.stderr)
            print(" " * (err.column - 1) + "^", file=sys.stderr)
            print(err, file=sys.stderr)
            raise

        # show result of parsing the input string
        # if debug_flag:
        print(input_string, "->", L)
        print("exprStack=", exprStack)

        # Evaluate the stack of parsed operands, emitting C code.
        try:
            result = _evaluateStack(exprStack)
            print(result)
        except TypeError:
            print(
                "Unsupported operation on right side of '%s'.\nCheck for missing or incorrect tags on non-scalar operands."
                % input_string,
                file=sys.stderr,
            )
            raise
        except UnaryUnsupportedError:
            print(
                "Unary negation is not supported for vectors and matrices: '%s'" % input_string,
                file=sys.stderr,
            )
            raise

        # Create final assignment and print it.
        # if debug_flag:
        print("var=", targetvar)
        if targetvar != None:
            try:
                result = _assignfunc(targetvar, result)
            except TypeError:
                print(
                    "Left side tag does not match right side of '%s'" % input_string,
                    file=sys.stderr,
                )
                raise
            except UnaryUnsupportedError:
                print(
                    "Unary negation is not supported for vectors and matrices: '%s'" % input_string,
                    file=sys.stderr,
                )
                raise

            return result
        else:
            print("Empty left side in '%s'" % input_string, file=sys.stderr)
            raise TypeError


##-----------------------------------------------------------------------------------
def fprocess(infilep, outfilep):
    """
    Scans an input file for LA equations between double square brackets,
    e.g. [[ M3_mymatrix = M3_anothermatrix^-1 ]], and replaces the expression
    with a comment containing the equation followed by nested function calls
    that implement the equation as C code. A trailing semi-colon is appended.
    The equation within [[ ]] should NOT end with a semicolon as that will raise
    a ParseException. However, it is ok to have a semicolon after the right brackets.

    Other text in the file is unaltered.

    The arguments are file objects (NOT file names) opened for reading and
    writing, respectively.
    """
    pattern = r"\[\[\s*(.*?)\s*\]\]"
    eqn = re.compile(pattern, re.DOTALL)
    s = infilep.read()

    def parser(mo):
        ccode = parse(mo.group(1))
        return "/* %s */\n%s;\nLAParserBufferReset();\n" % (mo.group(1), ccode)

    content = eqn.sub(parser, s)
    outfilep.write(content)


##----------------------------------------------------------------------------
## The following is executed only when this module is executed as
## command line script.  It runs a small test suite (see above)
## and then enters an interactive loop where you
## can enter expressions and see the resulting C code as output.

if __name__ == "__main__":
    import sys

    # input_string
    input_string = ""

    # Display instructions on how to use the program interactively
    interactiveusage = """
  Entering interactive mode:
  Type in an equation to be parsed or 'quit' to exit the program.
  Type 'debug on' to print parsing details as each string is processed.
  Type 'debug off' to stop printing parsing details
  """
    print(interactiveusage)
    input_string = input("> ")

    while input_string != "quit":
        try:
            print(parse(input_string))
        except Exception:
            pass

        # obtain new input string
        input_string = input("> ")

    # if user types 'quit' then say goodbye
    print("Good bye!")
    import os

    os._exit(0)
