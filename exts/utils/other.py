from __future__ import division
from decimal import Decimal
from pyparsing import (
    Literal,
    Word,
    Group,
    Forward,
    alphas,
    alphanums,
    Regex,
    ParseException,
    CaselessKeyword,
    Suppress,
    delimitedList,
)
import math
import operator

PHI = (1 + math.sqrt(5)) / 2


class NumericStringParser(object):
    """
    Most of this code comes from the fourFn.py pyparsing example by Paul McGuire

    http://pyparsing.wikispaces.com/file/view/fourFn.py
    http://pyparsing.wikispaces.com/message/view/home/15549426
    """

    def pushFirst(self, toks):
        self.exprStack.append(toks[0])

    def pushUMinus(self, toks):
        if toks and toks[0] == "-":
            self.exprStack.append("unary -")

    def __init__(self):
        """
        expop   :: '^' | '**'
        multop  :: '*' | '/' | '%'
        addop   :: '+' | '-'
        integer :: ['+' | '-'] '0'..'9'+
        atom    :: PI | E | real | fn '(' expr ')' | '(' expr ')'
        factor  :: atom [ expop factor ]*
        term    :: factor [ multop factor ]*
        expr    :: term [ addop term ]*
        """
        point = Literal(".")

        e = CaselessKeyword("E")
        pi = CaselessKeyword("PI")
        phi = CaselessKeyword("PHI")
        tau = CaselessKeyword("TAU")

        # fnumber = Combine(
        #     Word("+-" + nums, nums)
        #     + Optional(point + Optional(Word(nums)))
        #     + Optional(e + Word("+-" + nums, nums))
        # )
        fnumber = Regex(r"[+-]?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?")
        ident = Word(alphas, alphanums + "_$")

        plus, minus, mult, div, mod = map(Literal, "+-*/%")
        lpar, rpar = map(Suppress, "()")
        addop = plus | minus
        multop = mult | div | mod
        expop = Literal("^") | Literal("**")

        expr = Forward()
        expr_list = delimitedList(Group(expr))
        # add parse action that replaces the function identifier with a (name, number of args) tuple
        def insert_fn_argcount_tuple(t):
            fn = t.pop(0)
            num_args = len(t[0])
            t.insert(0, (fn, num_args))

        fn_call = (ident + lpar - Group(expr_list) + rpar).setParseAction(
            insert_fn_argcount_tuple
        )
        atom = (
            addop[...]
            + (
                (fn_call | pi | phi | e | tau | fnumber | ident).setParseAction(self.pushFirst)
                | Group(lpar + expr + rpar)
            )
        ).setParseAction(self.pushUMinus)

        # by defining exponentiation as "atom [ ^ factor ]..." instead of
        # "atom [ ^ atom ]...", we get right-to-left exponents, instead of left-to-right
        # that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = Forward()
        factor <<= atom + (expop + factor).setParseAction(self.pushFirst)[...]
        term = factor + (multop + factor).setParseAction(self.pushFirst)[...]
        expr <<= term + (addop + term).setParseAction(self.pushFirst)[...]

        self.bnf = expr

        # map operator symbols to corresponding arithmetic operations
        epsilon = 1e-12
        self.opn = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "/": operator.truediv,
            "%": operator.mod,
            "^": operator.pow,
            "**": operator.pow,
        }
        self.fn = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "atan": math.atan,
            "exp": math.exp,
            "abs": abs,
            "trunc": int,
            "round": round,
            "sgn": lambda a: -1 if a < -epsilon else 1 if a > epsilon else 0,
            "sqrt": math.sqrt,
            "floor": math.floor,
            "fact": math.factorial,
            # functionsl with multiple arguments
            "multiply": lambda a, b: a * b,
            "hypot": math.hypot,
            # functions with a variable number of arguments
            "all": lambda *a: all(a),
        }

    def evaluateStack(self, s):
        op, num_args = s.pop(), 0
        if isinstance(op, tuple):
            op, num_args = op

        if op == "unary -":
            return -self.evaluateStack(s)
        if op in self.opn:
            op2 = self.evaluateStack(s)
            op1 = self.evaluateStack(s)
            return self.opn[op](op1, op2)
        elif op == "PI":
            return math.pi  # 3.1415926535
        elif op == "E":
            return math.e  # 2.718281828
        elif op == "PHI":
            return PHI
        elif op == "TAU":
            return math.tau
        elif op in self.fn:
            # note: args are pushed onto the stack in reverse order
            args = reversed([self.evaluateStack(s) for _ in range(num_args)])
            return self.fn[op](*args)
        elif op[0].isalpha():
            return 0
        else:
            return Decimal(op)

    def eval(self, num_string, parseAll=True):
        self.exprStack = []
        results = self.bnf.parseString(num_string, parseAll)
        val = self.evaluateStack(self.exprStack[:])
        return val

if __name__ == "__main__":
    # For testing
    print(NumericStringParser().eval("63**57") > 2147483647)
