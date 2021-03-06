from pyrser.parsing.node import Node
from cnorm import nodes

from weakref import ref

# Expression
#--------------------------------

class KcExpr(nodes.Expr):
    """Base for all kooc expressions"""

    def __init__(self):
        """
        expr_type (None | type | ref(type) | array of type): The expression type
        """
        Node.__init__(self)
        self.expr_type = None

class KcLookup(KcExpr):
    """Kooc type lookup"""

    def __init__(self, context, member):
        KcExpr.__init__(self)
        self.context = context
        self.member = member

class KcCall(KcExpr):
    """Kooc type/instance call node"""

    def __init__(self, context, function, params):
        KcExpr.__init__(self)
        self.context = context
        self.function = function
        self.params = params

# Top level
#--------------------------------

class KcTopLevel:
    pass

class KcImport(KcTopLevel):
    """@import node"""

    def __init__(self, fullpath, name):
        self.file_fullpath = fullpath
        self.file_name = name

class KcModule(nodes.BlockStmt, KcTopLevel):
    """@module node"""

    def __init__(self, name):
        nodes.BlockStmt.__init__(self, [])
        KcTopLevel.__init__(self)
        self.name = name

    def init_from_blockstmt(self, name):
        KcTopLevel.__init__(self)
        self.__class__ = KcModule
        self.name = name

class KcImplementation(nodes.BlockStmt, KcTopLevel):
    """@implementation node"""

    def __init__(self, name):
        nodes.BlockStmt.__init__(self, [])
        KcTopLevel.__init__(self)
        self.name = name

    def init_from_blockstmt(self, name):
        KcTopLevel.__init__(self)
        self.__class__ = KcImplementation
        self.name = name

class KcModuleImplementation(KcImplementation):
    """@implementation for a module"""

class KcClassImplementation(KcImplementation):
    """@implementation for a class"""

class KcClass(KcModule):
    """@class node"""

    def __init__(self, name):
        KcModule.__init__(self, name)
        self.parents = []

    def init_from_blockstmt(self, name):
        KcModule.init_from_blockstmt(self, name)
        self.__class__ = KcClass
        self.parents = []

class KcMemberDecl(nodes.Decl):
    """class member decl (variable, not function)"""

class KcMethodDecl(nodes.Decl):
    """class method decl"""

class KcVirtualDecl(nodes.Decl):
    """class method decl"""

# Misc
#--------------------------------

class KcId(nodes.Id):
    """A kooc Id"""

class KcTypedLiteral(nodes.Literal):
    """C literal, with kooc type"""

    def __init__(self, value : str, typ):
        nodes.Literal.__init__(self, value)
        self.expr_type = typ

