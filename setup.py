# -*- coding: utf-8 -*-
#
# Copyright © 2020 NXP
# Copyright © 2020-2021 Chris Reed
#
# SPDX-License-Identifier: BSD-3-Clause
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# o Redistributions of source code must retain the above copyright notice, this list
#   of conditions and the following disclaimer.
#
# o Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
# o Neither the names of the copyright holders nor the names of the
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from setuptools import setup, find_packages

with open('README.md', encoding='utf-8') as readme_file:
    README = readme_file.read()

setup(
    name='pyocd-pemicro',
    use_scm_version={
        'local_scheme': 'dirty-tag',
        'write_to': 'pyocd_pemicro/_version.py'
    },
    description='PyOCD debug probe plugin for PEMicro debug probes',
    long_description_content_type="text/markdown",
    long_description=README,
    platforms="Windows, Linux, macOS",
    license='BSD-3-Clause',
    packages=find_packages(),
    author='Petr Gargulak, Chris Reed',
    author_email='petr.gargulak@nxp.com, chris.reed@arm.com',
    keywords=['PEMicro', 'PyPEMicro', 'PyOCD', 'PyOCD Plugin'],
    url='https://github.com/pyocd/pyocd-pemicro',
    download_url='https://pypi.org/project/pyocd_pemicro/',
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
        'License :: OSI Approved :: BSD License',
        'Topic :: Scientific/Engineering',
        "Topic :: Software Development :: Debuggers",
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: System :: Hardware',
        'Topic :: Utilities'
        ],
    python_requires=">=3.6",
    setup_requires=[
        'setuptools>=40.0',
        'setuptools_scm!=1.5.3,!=1.5.4',
        'setuptools_scm_git_archive',
        ],
    install_requires = [
        'pypemicro==0.1.6',
        ],
    entry_points={
        'pyocd.probe': [
            'pemicro = pyocd_pemicro:PEMicroProbePlugin',
        ],
    },
    zip_safe=True,
)
