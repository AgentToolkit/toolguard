import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

jsonpath = "/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final copy 4/BookReservation.json"
with open(jsonpath, "r") as file:
    json_data = json.load(file)


# Create a Tkinter window
root = tk.Tk()
root.title("Policy Tree Viewer & Editor")
root.geometry("600x400")

# Treeview for displaying the policies
tree = ttk.Treeview(root)
tree.pack(fill=tk.BOTH, expand=True)

# To store item currently selected for editing
selected_item = None


def populate_tree(data):
    """
    Populate the tree view with the JSON data structure.
    """
    for policy in data["policies"]:
        policy_node = tree.insert("", "end", text=policy["policy_name"], open=True)
        tree.insert(policy_node, "end", text="Description: " + policy["description"])
        references_node = tree.insert(policy_node, "end", text="References", open=True)
        for ref in policy["references"]:
            tree.insert(references_node, "end", text=ref)
        violating_node = tree.insert(
            policy_node, "end", text="Violating Examples", open=True
        )
        for example in policy["violating_examples"]:
            tree.insert(violating_node, "end", text=example)
        compliance_node = tree.insert(
            policy_node, "end", text="Compliance Examples", open=True
        )
        for example in policy["compliance_examples"]:
            tree.insert(compliance_node, "end", text=example)


def on_item_selected(event):
    """
    Handle the selection of an item in the tree.
    If a reference or example is selected, open the corresponding editor.
    """
    global selected_item
    selected_item = tree.selection()[0]
    item_text = tree.item(selected_item, "text")

    # If a reference or example is clicked, open it for viewing/editing
    if item_text.startswith("Example") or item_text.startswith("References"):
        # Display item for editing
        edit_item(item_text)


def edit_item(item_text):
    """
    Allow viewing or editing of the selected item (reference or example).
    """
    # Prompt for editing the text (view or edit)
    new_text = simpledialog.askstring(
        "Edit Text", "Edit the text:", initialvalue=item_text
    )
    if new_text is not None:
        # Update the tree with the new text
        tree.item(selected_item, text=new_text)
        messagebox.showinfo("Info", "Item updated successfully!")


def add_item():
    """
    Add a new policy to the tree.
    """
    policy_name = simpledialog.askstring("New Policy", "Enter policy name:")
    if policy_name:
        new_policy = {
            "name": policy_name,
            "description": "",
            "references": [],
            "violation_examples": [],
            "compliance_examples": [],
        }
        json_data["policies"].append(new_policy)
        tree.insert("", "end", text=policy_name)
        messagebox.showinfo("Info", f"Policy '{policy_name}' added.")


def save_json():
    """
    Save the current tree structure to a new JSON file.
    """
    with open("updated_policies.json", "w") as f:
        json.dump(json_data, f, indent=4)
    messagebox.showinfo("Info", "Changes saved to 'updated_policies.json'.")


def display_view_only():
    """
    Set all the references and examples to 'view only' mode.
    """
    for item in tree.get_children():
        # Find references and examples nodes and make them view-only
        if tree.item(item)["text"] == "References" or tree.item(item)[
            "text"
        ].startswith("Example"):
            tree.item(item, tags="view_only")


# Populate the tree with data from the JSON file
populate_tree(json_data)

# Bind the event for selecting an item
tree.bind("<<TreeviewSelect>>", on_item_selected)

# Buttons for adding items and saving the tree
add_button = tk.Button(root, text="Add Policy", command=add_item)
add_button.pack(side=tk.LEFT, padx=10)

save_button = tk.Button(root, text="Save", command=save_json)
save_button.pack(side=tk.LEFT, padx=10)

view_button = tk.Button(root, text="View Only Mode", command=display_view_only)
view_button.pack(side=tk.LEFT, padx=10)

root.mainloop()
