from setuptools import find_packages, setup

setup(
    name="esports",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    # The UI and SQL files ship inside the package.
    package_data={"esports": ["static/*", "sql/*.sql"]},
    install_requires=["flask", "PyMySQL"],
    python_requires=">=3.9",
)
