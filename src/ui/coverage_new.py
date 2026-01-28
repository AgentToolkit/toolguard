import argparse
import json
import os
import re
from collections import defaultdict
from typing import Dict, List

import markdown  # type: ignore[import]
from bs4 import BeautifulSoup
from flask import Flask, render_template, request
from unidecode import unidecode

app = Flask(__name__)


def normalize(text):
    """Normalize text: lowercase, remove punctuation, accents, quotes, html tags"""
    text = unidecode(text).lower()
    text = re.sub(r"[\"'`]", "", text)  # remove quotes
    text = re.sub(r"<[^>]+>", "", text)  # remove HTML tags
    text = re.sub(r"[^\w\s]", "", text)  # remove punctuation
    text = re.sub(r"\s+", " ", text)  # normalize whitespace
    return text.strip()


def find_approximate_matches(original_html, normalized_html, sentence_norm_to_orig):
    """Find approximate locations in original_html for normalized sentences and highlight"""
    highlighted_html = original_html
    offset = 0  # character offset for inserting spans without breaking indices

    for norm_sentence, orig_sentences in sentence_norm_to_orig.items():
        for match in re.finditer(re.escape(norm_sentence), normalized_html):
            start_idx = match.start()
            end_idx = match.end()

            # Find matching original text slice
            orig_start = find_original_index(normalized_html, original_html, start_idx)
            orig_end = find_original_index(normalized_html, original_html, end_idx)

            if orig_start is None or orig_end is None:
                continue

            # Extract actual matched text and wrap it
            matched_text = original_html[orig_start:orig_end]
            replacement = f'<span class="highlight">{matched_text}</span>'

            highlighted_html = (
                highlighted_html[: orig_start + offset]
                + replacement
                + highlighted_html[orig_end + offset :]
            )

            offset += len(replacement) - len(matched_text)
            break  # Highlight only once per sentence

    return highlighted_html


def find_original_index(normalized_html, original_html, norm_index):
    """Map normalized index to original HTML index"""
    norm_cursor = 0
    orig_cursor = 0
    while norm_cursor < norm_index and orig_cursor < len(original_html):
        c = original_html[orig_cursor]
        norm_c = normalize(c)
        if norm_c:
            norm_cursor += len(norm_c)
        orig_cursor += 1
    return orig_cursor if norm_cursor >= norm_index else None


def highlight_tool_sentences(doc, tools_data, selected_tools):
    """Main function to highlight sentences for selected tools in doc"""
    # Step 1: Parse to HTML (in case input is Markdown)
    if "<html" not in doc.lower() and "<body" not in doc.lower():
        html_doc = markdown.markdown(doc)
    else:
        html_doc = doc

    # Step 2: Remove HTML tags for normalized matching
    soup = BeautifulSoup(html_doc, "html.parser")
    clean_text = soup.get_text()

    # Step 3: Normalize the document
    normalized_doc = normalize(clean_text)

    # Step 4: Collect all normalized sentences from selected tools
    sentence_norm_to_orig = defaultdict(set)
    for tool in selected_tools:
        for sentence in tools_data.get(tool, []):
            norm = normalize(sentence)
            sentence_norm_to_orig[norm].add(sentence)

    # Step 5: Highlight in HTML
    highlighted_html = find_approximate_matches(
        html_doc, normalized_doc, sentence_norm_to_orig
    )
    return highlighted_html


@app.route("/")
def index():
    return render_template("coverage.html", text=policy_text, tools=tools_data)


@app.route("/highlight", methods=["POST"])
def highlight():
    selected_tools = request.json.get("tools", [])
    # highlights = set()
    # for tool in selected_tools:
    # 	if tool in normalized_passages:
    # 		highlights.update(normalized_passages[tool])

    highlighted_text = highlight_tool_sentences(
        policy_text, normalized_passages, selected_tools
    )

    # return {"highlights": list(highlights), "updated_text": highlighted_text}

    return {"updated_text": highlighted_text}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="parser")
    # parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki-with-salesforce-policies.md')
    # parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final with salesforce')
    # parser.add_argument('--policy-path', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki-with-policies-for-non-existing-tools.md')
    # parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki-with-salesforce-policies-rev.md')
    # parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki-with-policies-for-non-existing-tools-rev.md')
    # parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final non existing tools')
    parser.add_argument(
        "--policy-path",
        type=str,
        default="/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki.md",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="/Users/naamazwerdling/Documents/OASB/policy_validation/airline/GroundTruth",  # pragma: allowlist secret
    )
    # parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final')
    # parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final copy 4')
    # parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final_non-existing-tools-rev')
    # parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final wiki-with-salesforce-policies-rev')
    args = parser.parse_args()
    policy_path = args.policy_path
    outdir = args.outdir
    # policy_text = open(policy_path, 'r', encoding='utf-8').read()
    with open(policy_path, "r", encoding="utf-8") as f:
        policy_text = markdown.markdown(f.read())
    # policy_text = f.read()
    tools_data: Dict[str, List] = defaultdict(list)
    for filename in os.listdir(outdir):
        if filename.endswith(".json"):
            name = filename.replace(".json", "")
            print(name)
            with open(
                os.path.join(outdir, filename),
            ) as f:
                data = json.load(f)
                if isinstance(data["policy_items"], str):
                    continue
                for p in data["policy_items"]:
                    for r in p["references"]:
                        tools_data[name].append(r)
    tools_data = dict(sorted(tools_data.items()))

    # def normalize_text(text):
    # 	text = text.replace("“", '""').replace("”", '"')
    # 	text = text.replace("\'", '"')
    # 	text = text.replace("‘", "'").replace("’", "'")
    # 	text = text.replace("<p>", "")
    # 	text = re.sub(r'\s+', ' ', text).strip()
    # 	return text.lower()

    # Preprocess tool passages for better search
    normalized_passages = {
        tool: [p for p in passages] for tool, passages in tools_data.items()
    }

    app.run(debug=True, port=5002)
