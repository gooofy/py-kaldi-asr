from distutils.core import setup
from distutils.extension import Extension
import numpy

try:
    from Cython.Distutils import build_ext
except ImportError:
    use_cython = False
else:
    use_cython = True

cmdclass = { }
ext_modules = [ ]

if use_cython:
    ext_modules += [
        Extension("kaldisimple.nnet3", 
                  sources  = [ "kaldisimple/nnet3.pyx", "kaldisimple/nnet3_wrappers.cpp" ],
                  language = "c++",),
    ]
    cmdclass.update({ 'build_ext': build_ext })
else:
    ext_modules += [
        Extension("kaldisimple.nnet3", 
                  sources  = [ "kaldisimple/nnet3.cpp", "kaldisimple/nnet3_wrappers.cpp" ],
                  language = "c++",),
    ]

setup(
    name        = 'kaldisimple',
    # ...
    cmdclass    = cmdclass,
    ext_modules = ext_modules,
    include_dirs = [numpy.get_include()]
    )



# from distutils.core import setup
# from Cython.Build import cythonize
# import numpy
# 
# setup(ext_modules = cythonize(
#            "kaldisimple/kaldi_simple.pyx",               
#            sources  = ["kaldisimple/KaldiSimple.cpp"],  
#            language = "c++",
#       ),
#       include_dirs = [numpy.get_include()]
#      )
#

