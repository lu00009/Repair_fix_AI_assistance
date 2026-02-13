
DEBUG_LOG = "/home/lelo/projects/Repair_fix_AI_assistance/debug_trace.log"

def debug_print(msg):
    with open(DEBUG_LOG, "a") as f:
        f.write(msg + "\n")
    print(msg)
