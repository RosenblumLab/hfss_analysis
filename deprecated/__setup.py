import setuptools

with open("../README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="HFSS_pyEPR_helpers",
    version="0.0.1",
    author="RosenblumGroup",
    author_email="",
    description="",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    install_requires=[
        'pandas',
        'numpy',
        'pyEPR-quantum',
        'tqdm',
        'tabulate',
        'matplotlib',
    ],
)