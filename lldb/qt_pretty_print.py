import lldb
from builtins import chr


def qstring_summary(value, internal_dict):
    # try:
    data_ptr = value.GetChildMemberWithName("d")
    # Debugging information: print children of `d`
    num_children = d.GetNumChildren()
    children_info = [d.GetChildAtIndex(i).GetName() for i in range(num_children)]
    print(f"Children of d: {children_info}")

    return "unknown"

    length = (
        value.GetChildMemberWithName("d")
        .GetChildMemberWithName("size")
        .GetValueAsUnsigned()
    )
    return str(data_ptr)
    # return data_ptr.GetSummary().strip('"')[:length]


class QStringPrinter:
    "Print a QString"

    def __init__(self, val):
        self.val = val

    def to_string(self):

        d = self.val["d"]
        data = d.reinterpret_cast(gdb.lookup_type("char").pointer()) + d["offset"]
        data_len = d["size"] * gdb.lookup_type("unsigned short").sizeof
        return data.string("utf-16", "replace", data_len)

        # Access the internal data structure of QString
        d = self.val["d"]

        # Check if QString is null or empty
        if d == 0:
            print("d == 0")
            return "null"  # Handle null QStrings
        elif d["size"] == 0:
            print("d size == 0")
            return '""'  # Handle empty QStrings

        # Get the QChar array
        data = d["data"]

        # Get the size of the string
        size = int(d["size"])

        # Extract the characters
        string = []
        for i in range(size):
            qchar = data[i]
            char = chr(int(qchar["ucs"]))
            string.append(char)

        # Join the list into a single string
        return "".join(string)


def qstring_summary(val, internal_dict):
    if str(val.type) == "QString":
        return QStringPrinter(val)
    return None


def QString_SummaryProvider(valobj, internal_dict):
    def make_string_from_pointer_with_offset(F, OFFS, L):
        strval = 'u"'
        try:
            data_array = F.GetPointeeData(0, L).uint16
            for X in range(OFFS, L):
                V = data_array[X]
                if V == 0:
                    break
                strval += chr(V)
        except:
            pass
        strval = strval + '"'
        return strval.encode("utf-8")

    # qt5
    def qstring_summary(value):
        try:
            d = value.GetChildMemberWithName("d")
            # have to divide by 2 (size of unsigned short = 2)
            offset = d.GetChildMemberWithName("offset").GetValueAsUnsigned() / 2
            size = get_max_size(value)
            return make_string_from_pointer_with_offset(d, offset, size)
        except:
            print("?????????????????????????")
            return value

    def get_max_size(value):
        _max_size_ = None
        try:
            debugger = value.GetTarget().GetDebugger()
            _max_size_ = int(
                lldb.SBDebugger.GetInternalVariableValue(
                    "target.max-string-summary-length", debugger.GetInstanceName()
                ).GetStringAtIndex(0)
            )
        except:
            _max_size_ = 512
        return _max_size_

    return qstring_summary(valobj)


def breakpoint_callback(frame, bp_loc, dict):
    x_var = frame.FindVariable("this")
    class_name = x_var.GetType().GetName()
    print(f"Class name of variable 'this': {class_name}")
    return False
    if "PathItemBase" in class_name:
        return True
    return False


def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand(
        "type summary add -F qt_pretty_print.QString_SummaryProvider QString"
    )
    debugger.HandleCommand("type category enable qt")
