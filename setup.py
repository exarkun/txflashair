import setuptools

setuptools.setup(
    name="txflashair",
    version="0.0.1",
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "netifaces",
        "ipaddress",
        "treq",
    ],
    entry_points={
        "console_scripts": [
            "txflashair-sync = txflashair.sync:main",
            "txflashair-monitor = txflashair.monitor:main",
        ]
    },
)
