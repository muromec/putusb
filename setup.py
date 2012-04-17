#!/usr/bin/env python
#
# Copyright (C) 2009-2012
# 
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
# 
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
# 
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

from distutils.core import setup

setup(
    name='putusb',
    version='0.2',
    description='Python utility by Ilya Petrov (muromec) for low-level communication with some Motorola smartphones and also Tegra devices',
    author='Ilya Petrov (muromec)',
    author_email='ilya.muromec@gmail.com',
    license = 'BSD',
    url='https://github.com/muromec/putusb',
    packages=['putusb'],
    long_description =
"""
putusb is a utility by Ilya Petrov (muromec) for low-level communication with some Motorola smartphones and also Tegra devices. putusb runs on a host PC and communicates with the Tegra system (the AC100 in our case) through a dedicated USB port (the mini USB port on the AC100).
Unlike nvflash (which is distributed by nvidia as a binary only), putusb is a python script and should run on any system supported by PyUSB.
"""
)

