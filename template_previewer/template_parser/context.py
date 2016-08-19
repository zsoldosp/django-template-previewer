from django.template.base import Node, TextNode, VariableNode
from django.template.defaulttags import (
    CycleNode, FilterNode, FirstOfNode, ForNode, IfNode, IfChangedNode,
    IfEqualNode, LoadNode, NowNode, SpacelessNode, URLNode, WidthRatioNode,
    WithNode)

from django.template.loader import get_template
from django.template.loader_tags import (
    BlockNode, ExtendsNode, IncludeNode
)
from django.templatetags.i18n import TranslateNode, BlockTranslateNode
from django.utils.encoding import force_text
from django.utils import six


def _get_vars(filter_expression, only_filter_vars=False):
    """
    Return the list of vars used in a django filter expressions. That includes
    the main var and any filter arguments
    """
    result = []  # string literal or something like that
    has_var = hasattr(filter_expression.var, 'var')
    should_add_var_to_result = has_var and not only_filter_vars
    if should_add_var_to_result:
        result = [filter_expression.var.var]
    for _, arglist in filter_expression.filters:
        result.extend(arg.var for lookup, arg in arglist if lookup)
    return result


# The following are nodes that require no special treatment
_IGNORED_NODES = (TextNode, BlockNode, NowNode, LoadNode, SpacelessNode)


def _get_node_context(node):
    """
    Return the list of vars used in a node
    """
    result = []
    renames = []
    # Ignored nodes
    if isinstance(node, _IGNORED_NODES):
        pass
    # Simple variables
    elif isinstance(node, VariableNode):
        result = _get_vars(node.filter_expression)
    # Tags with arguments or some other magic
    elif isinstance(node, CycleNode):
        for expr in node.cyclevars:
            result += _get_vars(expr)
    elif isinstance(node, FilterNode):
        # The filter expr gets a "var|" prepended; so we remove it
        # with [1:]
        result = _get_vars(node.filter_expr)[1:]
    elif isinstance(node, FirstOfNode):
        for expr in node.vars:
            result += _get_vars(expr)
    elif isinstance(node, IfNode):
        for cond, subnode in node.conditions_nodelists:
            result += _get_expression_vars(cond)
    elif isinstance(node, IfChangedNode):
        for var in node._varlist:
            result += _get_vars(var)
    elif isinstance(node, IfEqualNode):
        result = _get_vars(node.var1) + _get_vars(node.var2)
    elif isinstance(node, IncludeNode):
        if hasattr(node.template, 'var'):
            included_template = get_template(node.template.var)
            result += get_context(included_template)
        for key, val in six.iteritems(node.extra_context):
            result += _get_vars(val)
        # Note that we ignore the included template and renaming here, because
        # We can not know which template is the one included
    elif isinstance(node, URLNode):
        result += _get_vars(node.view_name)
        for arg in node.args:
            result += _get_vars(arg)
        for key, arg in node.kwargs.items():
            result += _get_vars(arg)
    elif isinstance(node, WidthRatioNode):
        result = _get_vars(node.val_expr) + \
                 _get_vars(node.max_expr) + \
                 _get_vars(node.max_width)
    # Loading of another templates
    elif isinstance(node, ExtendsNode):
        if not hasattr(node.parent_name, 'var'): # literal
            parent = get_template(node.parent_name.literal)
            result += get_context(parent)
        if node.parent_name:
            result += _get_vars(node.parent_name)
    # Tags that introduce aliases to existing vars
    elif isinstance(node, ForNode):
        result = _get_vars(node.sequence)
        listvar = node.sequence.var.var.split(".")
        if len(node.loopvars) == 1:
            # Simple for
            renames = [([node.loopvars[0]], listvar + ["0"])]
        else:
            # Multi-variable for
            for i, loopvar in enumerate(node.loopvars):
                renames += [([loopvar], listvar + ["0", str(i)])]
    elif isinstance(node, WithNode):
        for key, val in node.extra_context.iteritems():
            if hasattr(val.var, 'var'):
                listval = val.var.var.split('.')
                renames += [([key], listval)]
    elif isinstance(node, TranslateNode):
        ignore_base_var = node.filter_expression.var.var[0] in ('\'', '"')
        result += _get_vars(node.filter_expression, only_filter_vars=ignore_base_var)
    elif isinstance(node, BlockTranslateNode):
        singular, vars = node.render_token_list(node.singular)
        result += vars
    else:
        tp_node = type(node)
        cls_name = '.'.join([tp_node.__module__, tp_node.__name__])
        custom_tag_base_cls_pre_19 = 'django.template.base.SimpleNode'
        custom_tag_base_cls_post_19 = 'django.template.library.SimpleNode'
        if cls_name in [custom_tag_base_cls_pre_19, custom_tag_base_cls_post_19]:
            if node.takes_context:
                class RecordContext(object):
                    autoescape = True

                    def __init__(self):
                        self.used_var_names = {}

                    def __repr__(self):
                        return repr(self.used_var_names)

                    def __getitem__(self, name):
                        self.used_var_names.setdefault(name, RecordContext())
                        return self.used_var_names[name]

                    def __getattr__(self, name):
                        return self[name]

                    def get_used_variable_names(self):
                        result = []
                        for name, child in self.used_var_names.items():
                            if not child.used_var_names:
                                result.append(name)
                            else:
                                full_names = list(
                                    '.'.join([name, child_name])
                                    for child_name in child.get_used_variable_names())
                                result.extend(full_names)
                        return sorted(result)

                record_context = RecordContext()
                node.render(record_context)
                result += record_context.get_used_variable_names()
        pass  # We can't do much if we don't know the etmplatetag meaning
    # TODO: regroup (the arg, and renamings)

    # Go through children nodes. [1:] is to skip self
    for attr in node.child_nodelists:
        nodelist = getattr(node, attr, None)
        if nodelist:
            for child_node in nodelist:
                result += _get_node_context(child_node)

    # Apply renames
    for src, dest in renames:
        l = len(src)
        for i, name in enumerate(result):
            chain = name.split('.')
            if chain[:l] == src:
                chain[:l] = dest
                result[i] = '.'.join(chain)
    return result


def _get_expression_vars(expr):
    """get variables used on an "if" expression"""
    result = []
    if hasattr(expr, 'value') and expr.value:
        def is_constant():
            empty_context = {}
            val = expr.eval(empty_context)
            are_same = force_text(val) == force_text(expr.value)
            return are_same
        if not is_constant():
            result += _get_vars(expr.value)
    if hasattr(expr, 'first') and expr.first:
        result += _get_expression_vars(expr.first)
    if hasattr(expr, 'second') and expr.second:
        result += _get_expression_vars(expr.second)
    return result


def get_context(template):
    """
    Returns a list of context variables used in the template. Each variable is
    represented as a dotted string from the context root.

    The argument is a template object, not just a filename.

    For example, passing the template {{ var }} {{ var.attribute }}
    Results in: ["var", "var.attribute"]

    And {% with local=var.attribute %}local.inner{% endwith %}
    Results in: ["var", "var.attribute", "var.attribute.inner"]

    Custom template tags may not be interpreted correctly, but any argument
    to a template tag that isn't quoted is used as a variable.
    """

    result = []
    for node in template.template.nodelist:
        result += _get_node_context(node)

    return result
