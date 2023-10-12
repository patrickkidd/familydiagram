pragma Singleton
import QtQml 2.12


QtObject {
    property int margins: 12
    
    function isDarkColor(color) {
        var temp = Qt.darker(color, 1) //Force conversion to color QML type object
        if(temp == null) {
            return false
        } else {
            var a = 1 - ( 0.299 * temp.r + 0.587 * temp.g + 0.114 * temp.b);
            return temp.a > 0 && a >= 0.3
        }
    }

}

