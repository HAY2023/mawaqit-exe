from setuptools import setup, find_packages

setup(
    name='mawaqit-exe',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        # Add any dependencies your package needs
    ],
    entry_points={
        'console_scripts': [
            # Add entry points for command line scripts if any
        ],
    },
    author='Your Name',
    author_email='your.email@example.com',
    description='A short description of the project.',
    url='https://github.com/HAY2023/mawaqit-exe',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        # Add more classifiers as needed
    ],
)