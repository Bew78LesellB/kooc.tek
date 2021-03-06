#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
This modules hold several function for mangling cnorm declaration
It may became a visitor or stay a function store, depending
on future of Kooc's implementation

It depend on cnorm.

Further documentation is written using reST syntax
"""

from cnorm.nodes import Decl, FuncType, PrimaryType, ComposedType, QualType, ParenType, PointerType, ArrayType, Signs, Specifiers, Storages, Qualifiers
from pyrser import grammar, meta, parsing, fmt
from pyrser.parsing import node
from .mangling_symboles import *

##################
#### MANGLING ####
##################

class Mangler:    

    # For use by caller of mangling:
    OriginIsModule = DECLARATION_FROM_MODULE
    OriginIsClass = DECLARATION_FROM_CLASS
    OriginIsInstance = DECLARATION_FROM_INSTANCE

    # Please don't change this
    TYPEFORMATSTRING = BEGINTYPE_SEPARATOR + '_{}_{}_{}_' + ENDTYPE_SEPARATOR #nodeType, nodeParameter, subType
    TYPEID = {
        (Signs.SIGNED, Specifiers.AUTO, 'char'): NATIVTYPE_SIGNED_CHAR,
        (Signs.AUTO, Specifiers.AUTO, 'char'): NATIVTYPE_CHAR,
        (Signs.UNSIGNED, Specifiers.AUTO, 'char'): NATIVTYPE_UNSIGNED_CHAR,
        (Signs.AUTO, Specifiers.SHORT, 'int'): NATIVTYPE_SHORT_INT,
        (Signs.UNSIGNED, Specifiers.SHORT, 'int'): NATIVTYPE_UNSIGNED_SHORT_INT,
        (Signs.AUTO, Specifiers.AUTO, 'int'): NATIVTYPE_INT,
        (Signs.UNSIGNED, Specifiers.AUTO, 'int'): NATIVTYPE_UNSIGNED_INT,
        (Signs.AUTO, Specifiers.LONG, 'int'): NATIVTYPE_LONG_INT,
        (Signs.UNSIGNED, Specifiers.LONG, 'int'): NATIVTYPE_UNSIGNED_LONG_INT,
        (Signs.AUTO, Specifiers.AUTO, 'float'): NATIVTYPE_FLOAT,
        (Signs.AUTO, Specifiers.AUTO, 'double'): NATIVTYPE_DOUBLE,
        (Signs.AUTO, Specifiers.LONG, 'double'): NATIVTYPE_LONG_DOUBLE,
        (Signs.AUTO, Specifiers.AUTO, 'void'): NATIVTYPE_VOID
    }
    
    def __init__(self, mangle_qualifiers = False):
        self.qualifierInSignature = mangle_qualifiers

    def _hasParams(self, node):
        """
        Check if node has an _params attribute

        :param node: the node who will be checked for _params attribute
        :type node: cnorm ast node
        :return: true if node has a _params attribute, else no
        :rtype: bool
        """
        return hasattr(node, '_params') and len(node._params)

    def _getParams(self, node):
        """
        Mangle node's parameters, including potential ellipsis

        :param node: the node whose parameters will be mangled
        :type node: cnorm ast node (supposed cnorm.nodes.ParenType or cnorm.nodes.FuncType)
        :return: mangled parameters of node
        :rtype: string
        """
        if not self._hasParams(node):
            return ''
        paramsRaw = [self.getType(param._ctype) for param in node._params];
        if hasattr(node, '_ellipsis') and node._ellipsis:
            paramsRaw.append(Mangler.TYPEFORMATSTRING.format(NODE_PRIMARYTYPE_CHAR, "{}_{}".format(USERTYPE_NATIV, NATIVTYPE_ELLIPSIS), Mangler.TYPEFORMATSTRING.format(NODE_NONETYPE_CHAR, '', '')))
        return '_'.join(paramsRaw)

    def _getQualifier(self, node):
        """
        Get the right qualifier mangling char from node

        :param node: node whose qualifier will be extracted
        :type node: cnorm ast node (supposed cnorm.nodes.QualType)
        :return: single letter describing the qualifier
        :rtype: string
        :raise Exception: if node's qualifier are unknown
        """
        qualifiers = {
            Qualifiers.CONST: QUALIFIER_CONST,
            Qualifiers.VOLATILE: QUALIFIER_VOLATILE
        }
        if node._qualifier in qualifiers:
            return qualifiers[node._qualifier]
        raise Exception('Unexpected qualifier: {}'.format(node._qualifier))

    def _getSign(self, node):
        """
        Get the node _sign attributes with a default value

        :param node: node whose sign will be extracted
        :type node: cnorm ast node (supposed cnorm.nodes.PrimaryType)
        :return: node signs, or cnorm.nodes.Signs.AUTO if unknown
        :rtype: integer (const from cnorm.nodes.Signs)
        """
        if hasattr(node, '_sign'):
            return node._sign;
        return Signs.AUTO;

    def _getSizeSpecifier(self, node):
        """
        Get the node _specifier with a default value

        :param ndeo: node whose specifier will be extracted
        :type node: cnorm ast node
        :return: node specifier, or cnorm.nodes.Specifiers.AUTO if unknown
        :rtype: integer (const from cnorm.nodes.Specifiers)
        """
        if hasattr(node, '_specifier'):
            return node._specifier
        return Specifiers.AUTO

    def _getNativType(self, node):
        """
        Get the mangling string for the node's final type

        :param node: node whose _identifier will be extracted
        :type node: cnorm ast node (supposed cnorm.nodes.PrimaryType)
        :return: mangling expression of node's identifier
        :rtype: string
        """
        identifier = (self._getSign(node), self._getSizeSpecifier(node), node._identifier)
        if identifier in Mangler.TYPEID:
            return '{}_{}'.format(USERTYPE_NATIV, Mangler.TYPEID[identifier])
        return '{}_{}_{}'.format(USERTYPE_TYPEDEF, len(node._identifier), node._identifier)

    def _getComposedType(self, node, specifier):
        """
        Get the mangling string for the node's final type

        :param node: node whose _identifier will be extracted
        :type node: cnorm ast node (supposed cnorm.nodes.ComposedType)
        ;param specifier: the node specifier
        :type specifier: int (sipposed from cnorm.nodes.Specifiers)
        :return: mangling expression of node's identifier
        :rtype: string
        """

        return '{}_{}_{}'.format(specifier, len(node._identifier), node._identifier)

    def _getFinalType(self, node):
        """
        Get the final type mangling string for both comosed and primary types

        :param node: node whose _identifier will be extracted
        :type node: cnorm ast node (supposed cnorm.nodes.ComposedType or cnorm.nodes.PrimaryType)
        :return: mangled final type
        :rtype: string
        """
        specifier = {
            Specifiers.UNION: USERTYPE_UNION,
            Specifiers.ENUM: USERTYPE_ENUM,
            Specifiers.STRUCT: USERTYPE_STRUCT
        };
        if node._specifier in specifier:
            return self._getComposedType(node, specifier[node._specifier])
        else:
            return self._getNativType(node)


    def getType(self, node):
        """
        Get the mangling string for the node's type

        :param node: node whose type will be extracted
        :type node: cnorm ast node
        :return: mangling expression of node's type
        :rtype: string
        :raises Exception: if node type is unknown
        """

        if isinstance(node, QualType):
            if self.qualifierInSignature:
                return Mangler.TYPEFORMATSTRING.format(NODE_QUALTYPE_CHAR, self._getQualifier(node), self.getType(node._decltype))
            return self.getType(node._decltype)
        elif isinstance(node, PointerType):
            return Mangler.TYPEFORMATSTRING.format(NODE_POINTERTYPE_CHAR, '', self.getType(node._decltype))
        elif isinstance(node, ArrayType):
            return Mangler.TYPEFORMATSTRING.format(NODE_ARRAYTYPE_CHAR, '', self.getType(node._decltype))
        elif isinstance(node, ParenType):
            return Mangler.TYPEFORMATSTRING.format(NODE_PARENTYPE_CHAR, self._getParams(node), self.getType(node._decltype))
        elif isinstance(node, FuncType):
            return Mangler.TYPEFORMATSTRING.format(NODE_FUNCTYPE_CHAR, self._getFinalType(node), self.getType(node._decltype))
        elif isinstance(node, ComposedType):
            return Mangler.TYPEFORMATSTRING.format(NODE_COMPOSEDTYPE_CHAR, self._getFinalType(node), self.getType(node._decltype))
        elif isinstance(node, PrimaryType):
            return Mangler.TYPEFORMATSTRING.format(NODE_PRIMARYTYPE_CHAR, self._getFinalType(node), self.getType(node._decltype))
        elif node is None:
            return Mangler.TYPEFORMATSTRING.format(NODE_NONETYPE_CHAR, '', '')
        else:
            raise Exception('Unexpected node : {}'.format(type(node)))

    def _getSymbolKind(self, ctype):
        """
        Get the mangling string for the node symbol kind

        :param ctype: ctype of node whose _identifier will be extracted
        :type ctype: cnorm ast ctype node
        :return: mangling expression of node's kind
        :rtype: string
        :raise Exception: ctype  has unexpected storage value
        """
        if ctype._storage is Storages.STATIC:
            return DECLARATION_STATIC
        elif ctype._storage is Storages.AUTO:
            return DECLARATION_AUTO
        elif ctype._storage is Storages.EXTERN:
            return DECLARATION_AUTO
        else:
            raise Exception('Unexpected storage : {}'.format(ctype._storage))

    def mangle_module(self, name, ctype, typeName, virtual=False):
        return self.mangle(name, ctype, DECLARATION_FROM_MODULE, typeName, virtual)

    def mangle_class(self, name, ctype, typeName, virtual=False):
        return self.mangle(name, ctype, DECLARATION_FROM_CLASS, typeName, virtual)

    def mangle(self, name, ctype, origin=DECLARATION_FROM_MODULE, typeName='', virtual=False):
        """
        Altere the declaration name to the declaration mangling string

        :param decl: decl whose name will be altered
        :type decl: cnorm ast node (supposed root of declaration)
        :param origin: the origin of the symbol: is it from a module, a class, or an instance of class. Validity of origin won't be checked, be carefull
        :type origin: value from mangling.OriginIs* (Module, Class, Instance) (ugly but python odesn't provide attribute on object so fuckit atm)
        :param modulName: the name of the module from which decl is from. May be empty if unknown (if mangling out of @import or @implement scope)
        :type modulName: string
        :param origin: origin of the the decl. Default to DECLARATION_FROM_MODULE
        :type origin: mangling.DECLARATION_FROM_[MODULE|INSTANCE|CLASS]
        :param typeName: the name of origin struct. Default to ""
        :type originNam: string
        :return: mangling expression of node's kind
        :rtype: cnorm ast node, same as the decl parameter
        """
        mangled_name = '{kindOfSymbol}_{typeDesc}_{origin}_{originNameSize}_{typeName}_{cSymbolSize}_{cSymbolName}'.format(
            kindOfSymbol=self._getSymbolKind(ctype),
            typeDesc=(self._getParams(ctype) + ('_' if self._hasParams(ctype) else '') + self.getType(ctype)),
            origin=origin,
            originNameSize=len(typeName),
            typeName=typeName,
            cSymbolSize=len(name),
            cSymbolName=name
        )
        if (virtual):
            mangled_name = DECORATOR_VIRTUAL + '_' + mangled_name
        return mangled_name

####################
#### UNMANGLING ####
####################

class Unmangler(grammar.Grammar):
    entry = "ini"
    grammar = format_mangling_string("""

    ini =               [@ignore("null") __scope__:params virtual? kindOfSymbol:kos [
                                        '_' type:type #addListedType(params, type)
                                ]+ '_' origin '_' identifier '_' identifier:cname #declRoot(_, kos, params, cname) eof]

    virtual =           ["{DECORATOR_VIRTUAL}" '_']

    origin =            ["{DECLARATION_FROM_MODULE}" | "{DECLARATION_FROM_CLASS}" | "{DECLARATION_FROM_INSTANCE}"]

    kindOfSymbol =      [
                                "{DECLARATION_AUTO}" #declAuto(_) |
                                "{DECLARATION_STATIC}" #declStatic(_)
                        ]

    type =              ["{BEGINTYPE_SEPARATOR}" '_' node:>_ '_' "{ENDTYPE_SEPARATOR}"]

    node =              [[
                                primaryType |
                                composedType |
                                funcType |
                                qualType |
                                pointerType |
                                arrayType |
                                parenType |
                                noneType
                        ]:>_]

    primaryType =       ["{NODE_PRIMARYTYPE_CHAR}" '_' finalTypeParameter:option #createPrimaryType(_, option)]

    composedType =      ["{NODE_COMPOSEDTYPE_CHAR}" '_' finalTypeParameter:option #createComposedType(_, option)]

    funcType =          ["{NODE_FUNCTYPE_CHAR}" '_' finalTypeParameter:option #createFuncType(_, option)]

    finalTypeParameter =        [
                                        [
                                                "{USERTYPE_TYPEDEF}" #typeTypedef(_) |
                                                "{USERTYPE_ENUM}" #typeEnum(_) |
                                                "{USERTYPE_UNION}" #typeUnion(_) |
                                                "{USERTYPE_STRUCT}" #typeStruct(_) |
                                                "{USERTYPE_NATIV}" #typeNativ(_)
                                        ]
                                        '_' [nativTypeChar:nativ #setNativType(_, nativ) | identifier:identifier #setUserType(_, identifier)] '_' type:type #setSubtype(_, type)
                                ]

    qualType =          ["{NODE_QUALTYPE_CHAR}" '_' ["{QUALIFIER_CONST}" | "{QUALIFIER_VOLATILE}"]:qualifier '_' type:type #createQualType(_, qualifier, type)]

    pointerType =       ["{NODE_POINTERTYPE_CHAR}" '_' '_' type:type #createPointerType(_, type)]

    arrayType =         ["{NODE_ARRAYTYPE_CHAR}" '_' '_' type:type #createArrayType(_, type)]

    parenType =         [
                                "{NODE_PARENTYPE_CHAR}" __scope__:params [
                                        ['_' '_' type:type #addListedType(params, type)] |
                                        ['_' type:type #addListedType(params, type)]+
                                ] #createParenType(_, params)
                        ]

    noneType =          ["{NODE_NONETYPE_CHAR}" '_' '_' #createNoneType(_)]

    nativTypeChar =     [
                                [
                                        "{NATIVTYPE_ELLIPSIS}" |
                                        "{NATIVTYPE_SIGNED_CHAR}" |
                                        "{NATIVTYPE_CHAR}" |
                                        "{NATIVTYPE_UNSIGNED_CHAR}" |
                                        "{NATIVTYPE_SHORT_INT}" |
                                        "{NATIVTYPE_UNSIGNED_SHORT_INT}" |
                                        "{NATIVTYPE_INT}" |
                                        "{NATIVTYPE_UNSIGNED_INT}" |
                                        "{NATIVTYPE_LONG_INT}" |
                                        "{NATIVTYPE_UNSIGNED_LONG_INT}" |
                                        "{NATIVTYPE_FLOAT}" |
                                        "{NATIVTYPE_DOUBLE}" |
                                        "{NATIVTYPE_LONG_DOUBLE}" |
                                        "{NATIVTYPE_VOID}"
                                ]:>_
                        ]

    identifier =        [num:identifierSize '_' [#consumeIdentifier(_, identifierSize)]]

    """)

    def unmangle(self, mangled_name):
        """
        WIP. Construct an abstract syntax tree from a mangling string
        Not fully implemented yet.
        Module name and other meta data are lost here.

        :param mangled_name: the mangled expression. It has to be valid.
        :type mangled_name: string (supposely return from mangle function)
        :return: the ast construced from mangled_name string
        :rtype: cnorm ast node
        """
        res = self.parse(mangled_name)
        return res

@meta.hook(Unmangler)
def declRoot(self, ast, kos, params, cname):
    subType = params.value[-1:][0]._ctype
    subType._storage = kos.value
    if params.ellipsis:
        subType._ellipsis = params.ellipsis
    try:
        subType._params = params.value[:-1]
    except:
        pass
    ast.set(Decl(cname.value, subType))
    return True

@meta.hook(Unmangler)
def declStatic(self, ast):
    ast.value = Storages.STATIC
    return True

@meta.hook(Unmangler)
def declAuto(self, ast):
    ast.value = Storages.AUTO
    return True

@meta.hook(Unmangler)
def consumeIdentifier(self, ast, size):
    """
    WIP. Put the size nth character in ast.value.
    Work with pyrser primitiv, should be heavyly tested so it doesn't fuck up pyrser
    """
    self._stream.save_context()
    self.begin_tag("id")
    for i in range(0, int(self.value(size))):
        if self.read_eof():
            return self._stream.restore_context()
        self._stream.incpos()
    self.end_tag("id");
    ast.value = str(self.get_tag("id"))
    return True;

@meta.hook(Unmangler)
def createPrimaryType(self, ast, opt):
    if not hasattr(opt, 'identifier'):
        ast.value = "ellipsis"
        return True
    ast.value = PrimaryType(opt.identifier)
    ast.value._specifier = opt.specifier
    ast.value._decltype = opt.decltype
    try:
        ast.value._sign = opt.sign
    except:
        pass
    return True

@meta.hook(Unmangler)
def createComposedType(self, ast, opt):
    ast.value = ComposedType(opt.identifier)
    ast.value._specifier = opt.specifier
    ast.value._decltype = opt.decltype
    try:
        ast.value._sign = opt.sign
    except:
        pass
    return True

@meta.hook(Unmangler)
def createFuncType(self, ast, opt):
    ast.value = FuncType(opt.identifier)
    ast.value._specifier = opt.specifier
    ast.value._decltype = opt.decltype
    try:
        ast.value._sign = opt.sign
    except:
        pass
    return True

@meta.hook(Unmangler)
def typeTypedef(self, ast):
    ast.specifier = Specifiers.AUTO
    return True

@meta.hook(Unmangler)
def typeEnum(self, ast):
    ast.specifier = Specifiers.ENUM
    return True

@meta.hook(Unmangler)
def typeUnion(self, ast):
    ast.specifier = Specifiers.UNION
    return True

@meta.hook(Unmangler)
def typeStruct(self, ast):
    ast.specifier = Specifiers.STRUCT
    return True

@meta.hook(Unmangler)
def typeNativ(self, ast):
    ast.specifier = Specifiers.AUTO
    return True

@meta.hook(Unmangler)
def setNativType(self, ast, nativNode):
    char = self.value(nativNode)
    if char == NATIVTYPE_ELLIPSIS:
        return True
    idSign = dict()
    for (key, value) in Mangler.TYPEID.items():
        idSign[value] = key
    if char in idSign:
        ast.sign = idSign[char][0]
        ast.specifier = idSign[char][1]
        ast.identifier = idSign[char][2]
        return True
    return False

@meta.hook(Unmangler)
def setUserType(self, ast, identifier):
    ast.identifier = identifier.value
    return True

@meta.hook(Unmangler)
def setSubtype(self, ast, subtype):
    ast.decltype = subtype.value
    return True

@meta.hook(Unmangler)
def createQualType(self, ast, qualifier, subtype):
    qualifiers = {
        QUALIFIER_CONST: Qualifiers.CONST,
        QUALIFIER_VOLATILE: Qualifiers.VOLATILE
    }
    if self.value(qualifier) in qualifiers:
        ast.value = QualType(qualifiers[self.value(qualifier)])
        ast.value._decltype = subtype.value
        return True
    return False

@meta.hook(Unmangler)
def createPointerType(self, ast, subtype):
    ast.value = PointerType()
    ast.value._decltype = subtype.value
    return True

@meta.hook(Unmangler)
def createArrayType(self, ast, subtype):
    ast.value = ArrayType()
    ast.value._decltype = subtype.value
    return True

@meta.hook(Unmangler)
def createNoneType(self, ast):
    ast.value = None
    return True

@meta.hook(Unmangler)
def createParenType(self, ast, params):
    ast.value = ParenType(params.value[:-1])
    if params.ellipsis:
        ast.value._ellipsis = params.ellipsis
    ast.value._decltype = params.value[-1:][0]._ctype
    return True

@meta.hook(Unmangler)
def initParams(self, ast):
    ast.value = []
    return True

@meta.hook(Unmangler)
def addListedType(self, typelist, subtype):
    if not hasattr(typelist, "value"):
        typelist.value = []
        typelist.ellipsis = False
    if subtype.value == "ellipsis":
        typelist.ellipsis = True
    else:
        typelist.value.append(Decl('', subtype.value))
    return True

