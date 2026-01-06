import os
import setuptools

if __name__ == '__main__':

    with open(os.path.join(os.path.dirname(__file__), "README.md"), "r") as fh:
        long_description = fh.read()

    setuptools.setup(
        name="framework-dataflow",
        version="0.0.0",
        author="Eduardo Luiz",
        author_email="eduardoluizgs@hotmail.com",
        description="Biblioteca para Fluxo de Dados",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="",
        packages=setuptools.find_packages(),
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ],
    )
