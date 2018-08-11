from setuptools import setup
import os.path

setupdir = os.path.dirname(__file__)

requirements = []
for line in open(os.path.join(setupdir, 'requirements.txt'), encoding="UTF-8"):
    if line.strip() and not line.startswith('#'):
        requirements.append(line)

setup(
      name="thonny-circuitpython",
      version="0.2b2",
      description="CircuitPython support for Thonny IDE",
      long_description="""Plug-in for Thonny IDE which adds CircuitPython backend. 
      
More info: 

* https://bitbucket.org/plas/thonny-circuitpython
* https://bitbucket.org/plas/thonny/wiki/MicroPython
* https://thonny.org
""",
      url="https://bitbucket.org/plas/thonny-circuitpython/",
      author="Aivar Annamaa",
	  author_email="aivar.annamaa@gmail.com",
      license="MIT",
      classifiers=[
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: End Users/Desktop",
        "License :: Freeware",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Education",
        "Topic :: Software Development",
        "Topic :: Software Development :: Embedded Systems",
      ],
      keywords="IDE education programming CircuitPython MicroPython Thonny",
      platforms=["Windows", "macOS", "Linux"],
      python_requires=">=3.5",
      include_package_data=True,
	  package_data={'thonnycontrib.circuitpython': ['api_stubs/*']},
      install_requires=requirements,
      packages=["thonnycontrib.circuitpython"],
)