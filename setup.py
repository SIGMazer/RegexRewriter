from setuptools import setup, find_packages


setup(
    name="RegexRewriter", 
    version="0.1.1",
    packages=find_packages(),
    install_requires=[
    ],
    author="Mazin Sayed (SIGMazer)",
    author_email="Mazinasd7@gamil.com   ",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/SIGMazer/RegexRewriter",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6", 
)

