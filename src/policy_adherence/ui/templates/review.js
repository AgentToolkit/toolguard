document.addEventListener("DOMContentLoaded", function () {
    const policyContainer = document.getElementById("policy-container");
    const saveButton = document.getElementById("save-btn");

    function loadPolicies() {
        fetch("/api/policies")
            .then(response => response.json())
            .then(data => {
                policyContainer.innerHTML = "";
                data.forEach(policy => addPolicyElement(policy));
                addAddButton(policyContainer);
            });
    }

    function addPolicyElement(policy, parentElement = policyContainer) {
        const div = document.createElement("div");
        div.classList.add("policy");

        const input = document.createElement("input");
        input.type = "text";
        input.value = policy.name;
        div.appendChild(input);

        const deleteIcon = document.createElement("span");
        deleteIcon.classList.add("delete-icon");
        deleteIcon.innerHTML = "❌";
        deleteIcon.onclick = () => {
            parentElement.removeChild(div);
        };
        div.appendChild(deleteIcon);

        if (policy.children) {
            const childContainer = document.createElement("div");
            policy.children.forEach(child => addPolicyElement(child, childContainer));
            div.appendChild(childContainer);
        }

        const addIcon = document.createElement("span");
        addIcon.classList.add("add-icon");
        addIcon.innerHTML = "➕";
        addIcon.onclick = () => {
            const newChild = { name: "New Policy", children: [] };
            addPolicyElement(newChild, div);
        };
        div.appendChild(addIcon);

        parentElement.appendChild(div);
    }

    function addAddButton(parentElement) {
        const addButton = document.createElement("button");
        addButton.textContent = "➕ Add Policy";
        addButton.onclick = () => {
            addPolicyElement({ name: "New Policy", children: [] }, parentElement);
        };
        parentElement.appendChild(addButton);
    }

    saveButton.addEventListener("click", function () {
        const policies = [];
        document.querySelectorAll("#policy-container > .policy").forEach(policyElement => {
            policies.push(serializePolicy(policyElement));
        });

        fetch("/api/policies", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(policies)
        }).then(() => alert("Policies saved successfully!"));
    });

    function serializePolicy(policyElement) {
        const name = policyElement.querySelector("input").value;
        const children = [];
        policyElement.querySelectorAll(":scope > div .policy").forEach(child => {
            children.push(serializePolicy(child));
        });
        return { name, children };
    }

    loadPolicies();
});
