import lldb


def breakpoint_callback(frame, bp_loc):
    x_var = frame.FindVariable("this")
    if x_var:
        class_name = x_var.GetType().GetName()
        if "PathItemBase" in class_name:
            print("found PathItemBase")
            return True
    print("not PathItemBase")
    return False


def handle_breakpoint_event(event):
    process = event.GetProcess()
    thread = process.GetSelectedThread()
    frame = thread.GetSelectedFrame()

    if thread.GetStopReason() == lldb.eStopReasonBreakpoint:
        bp_loc = thread.GetStopReasonDataAtIndex(
            0
        )  # Get the location where the breakpoint hit
        if breakpoint_callback(frame, bp_loc):
            print("Condition met, stopping at breakpoint.")
        else:
            print("Condition not met, continuing execution.")
            process.Continue()


def __lldb_init_module(debugger, internal_dict):
    # Create an event listener
    listener = debugger.GetListener()

    def event_callback(event, data):
        handle_breakpoint_event(event)

    # Register the event listener with LLDB
    listener.StartListeningForEvents(
        debugger.GetSelectedTarget().GetProcess(),
        lldb.SBProcess.eBroadcastBitStateChanged,
    )

    # Set the listener callback
    listener.SetEventCallback(event_callback)

    print("lldb_breakpoint.py script loaded.")
