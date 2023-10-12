.pragma library

function isEmptyObject(o) {
    return Object.entries(o).length == 0;
}

function isValidDateTime(d) {
    return d instanceof Date && !isNaN(d);
}

// this needs to go to a global js file
function arraysEqual(arr1, arr2) {
    if(arr1.length !== arr2.length)
        return false;
    for(var i = arr1.length; i--;) {
        if(arr1[i] !== arr2[i])
            return false;
    }
    
    return true;
}


function arrayRemove(arr, value) {
    const index = arr.indexOf(value);
    if(index < 0)
        return;
    arr.splice(index, 1);
}


// https://stackoverflow.com/questions/45029968/how-do-i-set-the-combobox-width-to-fit-the-largest-item
function ___calcComboBoxImplicitWidth(cb) {
  var widest = 0;
  if (cb.count===0) return cb.width;
  var originalCI = cb.currentIndex;
  if (originalCI < 0) return cb.width; // currentIndex →  deleted item
  do {
    widest = Math.max(widest, cb.contentItem.contentWidth);
    cb.currentIndex = (cb.currentIndex + 1) % cb.count;
  } while(cb.currentIndex !== originalCI)

  return widest + cb.contentItem.leftPadding + cb.contentItem.rightPadding
                + cb.indicator.width;
}



// Qt nuance:  QDateTime(QDate(1969, 10, 14)).offsetFromUtc() != QDateTime(QDate(1970, 10, 14)).offsetFromUtc()
function Date__equals(a, b) {
    return a.getTime() == b.getTime();
}

function Date__gt(a, b) {
    var _a = new Date(a.getFullYear(), a.getMonth(), a.getDate());
    var _b = new Date(b.getFullYear(), b.getMonth(), b.getDate());
    if(_a == _b) {
        return false;
    } else {
        return _a > _b;
    }
}

function Date__lt(a, b) {
    var _a = new Date(a.getFullYear(), a.getMonth(), a.getDate());
    var _b = new Date(b.getFullYear(), b.getMonth(), b.getDate());
    if(_a == _b) {
        return false;
    } else {
        return _a < _b;
    }
}

Number.prototype.clamp = function(min, max) {
  return Math.min(Math.max(this, min), max);
};

// function Date__gte(a, b) {
//     return ! Date__lt(a, b);
// }

// function Date__lte(a, b) {
//     return ! Date__lte(a, b);
// }


function printObject(obj) {
    function inner(innerObject, innerLevel) {
        innerLevel += 1;
        var spaces = '';
        for(var i=0; i < innerLevel; i++) {
            spaces += '    ';
        }
        for (var key in innerObject) {
            if (typeof innerObject[key] === "object") {
                console.log(spaces, key + ':');
                inner(innerObject[key], innerLevel);
            } else {
                console.log(spaces, key + ':', innerObject[key]);    
            }
        }
    }
    console.log(' ');
    console.log('--->' + (typeof obj) + ':');
    inner(obj, 0);
}


/////////////////////////////////////////////////
//
//  Server Http
//
/////////////////////////////////////////////////


var _lastServerId = 0
var _serverRequests = {}

function server(util, session, method, path, data, callback) {

    function onHTTPFinished(id, response) {        
        var entry = _serverRequests[id];        
        if(!entry) {
            // called multiple times per request; once for each request still in progress
            // but only one will match
            return
        }
        util.jsServerHttpFinished.disconnect(onHTTPFinished);
        if(response._data) {
            response.data = JSON.parse(response._data);
        };
        if(entry !== undefined) {
            _serverRequests[id].callback.call(undefined, response);
            delete _serverRequests[id];    
        }
    }

    _lastServerId += 1;
    util.jsServerHttpFinished.connect(onHTTPFinished);
    _serverRequests[_lastServerId] = {
        method: method,
        path: path,
        callback: callback
    };
    if(data === null) {
        util.jsServerHttp(session, _lastServerId, method, path);
    } else {
        util.jsServerHttp(session, _lastServerId, method, path, data);
    }
}

