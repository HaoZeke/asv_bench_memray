Development
===========

During development, one needs to pass a relative path:

.. code:: json

   "matrix": {
       "req": {
           "asv_bench_memray": ["../asv_bench_memray"]
       },
   },

Also it may be necessary to cleanup older environments and explicitly
point to an instance of ``asv_runner``:

.. code:: sh

   rm -rf .asv && ASV_RUNNER_PATH="../asv_runner" asv run --bench sum

Personally I keep benchmarks for testing at an `experiments
repo <https://github.com/HaoZeke/asv_experiments>`__, but any local test
will do.

Conventions
-----------

Like all externally defined benchmark plugins for ``asv``, this has a strict hierarchy:

- The package name begins with ``asv_bench``.
- Benchmarks are defined in a ``benchmarks`` folder under the package module.
- Each exported new benchmark type has the ``export_as_benchmark = [NAMEBenchmark]`` attribute.

For more conventions, follow the documentation of ``asv_runner``.

How a ``ray_*`` method is constructed
-------------------------------------

Write an ordinary class. ``asv_runner`` builds that class with no arguments,
then wraps each ``ray_*`` or ``Ray*`` method as
``RayMemBenchmark(name, func, attr_sources)``. Those three parameters are the
wrapper constructor. Assigning ``name``, ``func``, and ``attr_sources`` on
your class leaves that call empty.

A subclass of ``RayMemBenchmark`` is constructed with no arguments too, which raises::

    TypeError: RayMemBenchmark.__init__() missing 3 required positional arguments: 'name', 'func', and 'attr_sources'

Use a plain class instead:

.. code:: python

   class MyBenchmark:
       params = [10, 20000]

       def ray_sum(self, n):
           self.data = bytearray(n)

The requirements entry is the project ``asv_bench_memray``. On a conda
environment, request ``pip+asv-bench-memray`` so pip installs the PyPI
project. The ``memray-plugin`` branch of `asv_samples
<https://github.com/HaoZeke/asv_samples>`_ is a working copy of that layout.
