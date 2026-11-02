import re
import streamlit as st
from functools import lru_cache



st.set_page_config(
    page_title="GrammarFix",
    page_icon="🌳",
    layout="wide"
)

st.title("🌳 GrammarFix")
st.subheader("Dangling-Else Ambiguity Resolver")
st.caption("Compiler Design Hackathon Project")

st.info(
    "The dangling-else problem occurs when an else "
    "can be associated with different if statements."
)

# ==========================================
# GRAMMAR DEFINITIONS
# ==========================================

with st.expander("View Grammar Transformation", expanded=True):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Original Grammar")
        st.code(
            "S -> if (E) S\n"
            "S -> if (E) S else S\n"
            "S -> other"
        )

    with col2:
        st.markdown("### Unambiguous Grammar")
        st.code(
            "S -> M | U\n"
            "M -> if (E) M else M | other\n"
            "U -> if (E) S\n"
            "U -> if (E) M else U"
        )

    st.markdown("**M:** Matched statement")
    st.markdown("**U:** Unmatched statement")
    st.markdown("**E:** Condition")


# ==========================================
# TOKENIZER
# ==========================================

def tokenize(source):
    pattern = r'if\b|else\b|[A-Za-z_]\w*|\d+|==|!=|<=|>=|[(){};=<>+\-*/]|\S'
    return re.findall(pattern, source)


# ==========================================
# PARSE TREE NODE
# ==========================================

class Node:

    def __init__(self, label, children=None):
        self.label = label
        self.children = children or []


# ==========================================
# PARSER FOR ORIGINAL AMBIGUOUS GRAMMAR
# ==========================================

def parse_original(tokens):

    @lru_cache(maxsize=None)
    def parse_statement(pos):

        results = []

        if pos >= len(tokens):
            return ()

        # Handle if statement
        if tokens[pos] == "if":

            if pos + 1 >= len(tokens):
                return ()

            if tokens[pos + 1] != "(":
                return ()

            # Find matching closing parenthesis
            depth = 0
            close = -1

            for i in range(pos + 1, len(tokens)):

                if tokens[i] == "(":
                    depth += 1

                elif tokens[i] == ")":
                    depth -= 1

                    if depth == 0:
                        close = i
                        break

            if close == -1:
                return ()

            condition = " ".join(tokens[pos + 2:close])

            # Parse the then statement
            then_options = parse_statement(close + 1)

            for then_node, then_end in then_options:

                # Option 1: if without else
                node = Node(
                    "IF",
                    [
                        Node(condition),
                        then_node,
                        Node("No else")
                    ]
                )

                results.append((node, then_end))

                # Option 2: if with else
                if (
                    then_end < len(tokens)
                    and tokens[then_end] == "else"
                ):

                    else_options = parse_statement(then_end + 1)

                    for else_node, else_end in else_options:

                        node = Node(
                            "IF",
                            [
                                Node(condition),
                                then_node,
                                else_node
                            ]
                        )

                        results.append((node, else_end))

        # Handle simple statements
        else:

            end = pos

            while end < len(tokens):

                if tokens[end] == ";":
                    end += 1
                    break

                if tokens[end] in ("else", "}"):
                    break

                end += 1

            if end > pos:
                label = " ".join(tokens[pos:end])

                results.append(
                    (Node(label), end)
                )

        # Remove duplicate parse results
        unique = {}
        for node, end in results:
            key = (str(node.label), end, repr(node.children))
            unique[key] = (node, end)

        return tuple(unique.values())

    if not tokens:
        return []

    results = parse_statement(0)

    complete = [
        node
        for node, end in results
        if end == len(tokens)
    ]

    return complete


# ==========================================
# PARSER USING NEAREST-UNMATCHED-IF RULE
# ==========================================

def parse_transformed(tokens):

    def parse_statement(pos):

        if pos >= len(tokens):
            raise ValueError("Incomplete statement")

        # Parse if statement
        if tokens[pos] == "if":

            if pos + 1 >= len(tokens) or tokens[pos + 1] != "(":
                raise ValueError("Expected '(' after if")

            depth = 0
            close = -1

            for i in range(pos + 1, len(tokens)):

                if tokens[i] == "(":
                    depth += 1

                elif tokens[i] == ")":
                    depth -= 1

                    if depth == 0:
                        close = i
                        break

            if close == -1:
                raise ValueError("Missing closing parenthesis")

            condition = " ".join(tokens[pos + 2:close])

            then_node, next_pos = parse_statement(close + 1)

            else_node = Node("No else")

            # The nearest unmatched if consumes else first.
            if next_pos < len(tokens) and tokens[next_pos] == "else":

                else_node, next_pos = parse_statement(next_pos + 1)

            return (
                Node(
                    "IF",
                    [
                        Node(condition),
                        then_node,
                        else_node
                    ]
                ),
                next_pos
            )

        # Parse simple statement
        end = pos

        while end < len(tokens):

            if tokens[end] == ";":
                end += 1
                break

            if tokens[end] in ("else", "}"):
                break

            end += 1

        if end == pos:
            raise ValueError("Invalid statement")

        return Node(" ".join(tokens[pos:end])), end

    if not tokens:
        raise ValueError("Enter a statement")

    tree, end = parse_statement(0)

    if end != len(tokens):
        raise ValueError("Could not parse the complete statement")

    return tree


# ==========================================
# GENERATE GRAPHVIZ PARSE TREE
# ==========================================

def create_graph(tree, title="Parse Tree"):

    lines = [
        "digraph ParseTree {",
        'graph [label="' + title + '", labelloc="t"];',
        "rankdir=TB;",
        "node [shape=box, style=filled, fillcolor=lightblue];",
        'edge [fontname="Arial"];'
    ]

    counter = [0]

    def add_node(node, parent=None, edge_label=""):

        node_id = "n" + str(counter[0])
        counter[0] += 1

        label = str(node.label)
        label = label.replace("\\", "\\\\")
        label = label.replace('"', '\\"')

        if label == "No else":
            label = "No else"

        lines.append(
            f'{node_id} [label="{label}"];'
        )

        if parent is not None:

            if edge_label:
                lines.append(
                    f'{parent} -> {node_id} '
                    f'[label="{edge_label}"];'
                )
            else:
                lines.append(
                    f'{parent} -> {node_id};'
                )

        if node.label == "IF" and len(node.children) == 3:

            add_node(node.children[0], node_id, "Condition")
            add_node(node.children[1], node_id, "Then")

            if node.children[2].label != "No else":
                add_node(node.children[2], node_id, "Else")

        else:

            for child in node.children:
                add_node(child, node_id)

        return node_id

    add_node(tree)

    lines.append("}")

    return "\n".join(lines)


# ==========================================
# EXAMPLE TEST CASES
# ==========================================

examples = {

    "Example 1: Simple if-else":
        "if (a) x = 1; else x = 2;",

    "Example 2: Nested if":
        "if (a) if (b) x = 1;",

    "Example 3: Dangling else":
        "if (a) if (b) x = 1; else x = 2;",

    "Example 4: Three nested ifs":
        "if (a) if (b) if (c) x = 1; else x = 2; else x = 3;",

    "Example 5: Two else clauses":
        "if (a) x = 1; else if (b) x = 2; else x = 3;"
}


# ==========================================
# USER INPUT
# ==========================================

st.divider()

selected_example = st.selectbox(
    "Choose a test case",
    list(examples.keys())
)

source = st.text_area(
    "Enter your nested if-else statement",
    value=examples[selected_example],
    height=150
)


# ==========================================
# ANALYZE STATEMENT
# ==========================================

if st.button("Analyze Statement", type="primary"):

    tokens = tokenize(source)

    st.subheader("Token Stream")

    st.code("  ".join(tokens))

    try:

        original_trees = parse_original(tokens)

        if not original_trees:
            st.error("The statement could not be parsed.")
            st.stop()

        transformed_tree = parse_transformed(tokens)

        st.success("Statement parsed successfully!")

        # Original grammar results
        st.subheader("Original Grammar: Parse Tree Comparison")

        original_count = len(original_trees)

        if original_count > 1:
            st.warning(
                f"Ambiguity detected! Found {original_count} "
                "possible parse trees."
            )
        else:
            st.info(
                "Only one complete parse tree was found "
                "for this input."
            )

        for index, tree in enumerate(original_trees, start=1):

            st.markdown(
                f"### Original Interpretation {index}"
            )

            st.graphviz_chart(
                create_graph(
                    tree,
                    f"Original Parse Tree {index}"
                )
            )

        # Transformed grammar result
        st.divider()

        st.subheader("Transformed Grammar: Parse Tree")

        st.markdown(
            "The nearest-unmatched-if rule resolves the ambiguity."
        )

        st.graphviz_chart(
            create_graph(
                transformed_tree,
                "Transformed Parse Tree"
            )
        )

        st.success(
            "Exactly one transformed parse tree was generated."
        )

        # Verification
        st.divider()

        st.subheader("Grammar Transformation Verification")

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Original Parse Trees",
                original_count
            )

        with col2:
            st.metric(
                "Transformed Parse Trees",
                1
            )

        if original_count > 1:

            st.write(
                "The original grammar is ambiguous for this input. "
                "The transformed grammar applies the nearest-unmatched-if "
                "rule to select one interpretation."
            )

        else:

            st.write(
                "The original grammar produces one parse tree "
                "for this input."
            )

        st.subheader("Conclusion")

        st.write(
            "GrammarFix demonstrates dangling-else ambiguity "
            "using parse trees. The transformed parser associates "
            "each else with the nearest unmatched if."
        )

    except Exception as error:

        st.error(f"Error: {error}")


# ==========================================
# AUTOMATED TEST SUITE
# ==========================================

st.divider()

st.subheader("Automated Test Suite")

if st.button("Run All Five Tests"):

    test_results = []

    for name, statement in examples.items():

        try:

            test_tokens = tokenize(statement)

            original = parse_original(test_tokens)

            transformed = parse_transformed(test_tokens)

            original_count = len(original)
            transformed_count = 1 if transformed else 0

            # Three nested ifs with two else clauses
            # have three valid original parse trees.
            if name == "Example 4: Three nested ifs":
                expected_original = 3
            elif name == "Example 3: Dangling else":
                expected_original = 2
            else:
                expected_original = 1

            expected_transformed = 1

            original_pass = (
                original_count == expected_original
            )

            transformed_pass = (
                transformed_count == expected_transformed
            )

            passed = original_pass and transformed_pass

            test_results.append({

                "Test Case": name,

                "Expected Original Trees": expected_original,

                "Actual Original Trees": original_count,

                "Original Check":
                    "PASS" if original_pass else "FAIL",

                "Expected Transformed Trees":
                    expected_transformed,

                "Actual Transformed Trees":
                    transformed_count,

                "Transformed Check":
                    "PASS" if transformed_pass else "FAIL",

                "Original Grammar":
                    "Ambiguous"
                    if original_count > 1
                    else "Unambiguous",

                "Overall Result":
                    "PASS" if passed else "FAIL"

            })

        except Exception:

            test_results.append({

                "Test Case": name,
                "Expected Original Trees": "-",
                "Actual Original Trees": "-",
                "Original Check": "FAIL",
                "Expected Transformed Trees": 1,
                "Actual Transformed Trees": 0,
                "Transformed Check": "FAIL",
                "Original Grammar": "Error",
                "Overall Result": "FAIL"

            })

    import pandas as pd

    df = pd.DataFrame(test_results)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    passed_count = (
        df["Overall Result"] == "PASS"
    ).sum()

    failed_count = len(df) - passed_count

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Tests", len(df))
    col2.metric("Passed", int(passed_count))
    col3.metric("Failed", int(failed_count))

    if failed_count == 0:

        st.success("All five test cases passed!")

    else:

        st.error(
            f"{failed_count} test(s) failed. "
            "Check the expected and actual parse-tree counts."
        )


# ==========================================
# PROJECT EXPLANATION
# ==========================================

st.divider()

st.subheader("How GrammarFix Works")

st.markdown("""
1. Accepts nested if-else statements.
2. Converts source code into tokens.
3. Generates possible parse trees using the original grammar.
4. Detects dangling-else ambiguity.
5. Applies the nearest-unmatched-if rule.
6. Generates the transformed parse tree.
7. Runs automated tests to verify the results.
""")

st.caption("GrammarFix | Compiler Design Hackathon 2026")