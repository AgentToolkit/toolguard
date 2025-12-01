import sys
import importlib
from pathlib import Path
import multiprocessing

def process_target(queue, func, args, kwargs, extra_paths):
    try:
        # Add dynamic python paths
        if extra_paths:
            for p in extra_paths:
                p = str(Path(p).resolve())
                if p not in sys.path:
                    sys.path.insert(0, p)

        # Force reload of modules from those paths (optional)
        if extra_paths:
            for modname, module in list(sys.modules.items()):
                file = getattr(module, "__file__", None)
                if not file:
                    continue

                for p in extra_paths:
                    p = Path(p).resolve()
                    try:
                        if Path(file).resolve().is_relative_to(p):
                            importlib.reload(module)
                    except Exception:
                        pass

        # Run the function
        result = func(*args, **kwargs)
        queue.put(("ok", result))
    except Exception as e:
        queue.put(("error", e))

def run_in_process(func, *args, extra_paths=None, **kwargs):
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(
        target=process_target,
        args=(queue, func, args, kwargs, extra_paths)
    )
    p.start()
    p.join()

    status, value = queue.get()
    if status == "error":
        raise value
    return value
