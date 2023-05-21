from asvcore.benchmarks._base import Benchmark
from asvcore.benchmarks._exceptions import NotRequired

import uuid
import re

try:
    import memray
    from memray import FileReader
except ImportError:
    raise NotRequired("RayMemBenchmark not requested or memray not found")

class RayMemBenchmark(Benchmark):
    """
    A single benchmark for tracking the memory of an object with memray
    """

    name_regex = re.compile("^(Ray[A-Z_].+)|(ray_.+)$")

    def __init__(self, name, func, attr_sources):
        Benchmark.__init__(self, name, func, attr_sources)
        self.type = "memory"
        self.unit = "bytes"
        pass

    def run(self, *param):

        u_id = uuid.uuid4()
        temp_dir = tempfile.gettempdir()
        tfile_loc = Path(f"{temp_dir}/{u_id}.bin")
        with memray.Tracker(
            destination=memray.FileDestination(tfile_loc, overwrite=True)
        ):
            self.func(*param)
        freader = FileReader(str(tfile_loc))
        return freader.metadata.peak_memory

export_as_benchmark = [RayMemBenchmark]
