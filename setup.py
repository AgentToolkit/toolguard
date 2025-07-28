from setuptools import setup, find_packages

# Read the requirements from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="toolguard",
    version="0.1.0",
    description="Policy adherence code generation for guarding AI agent tools",
    author="Naama Zwerdling, David Boaz",
    author_email="naamaz@il.ibm.com, davidbo@il.ibm.com",
    packages=find_packages(where="src"),
    package_data={
        "toolguard": ["stages_tptd/prompts/*.txt","templates/*.j2"],
    },
    package_dir={"": "src"},
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # Adjust license if needed
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
)
