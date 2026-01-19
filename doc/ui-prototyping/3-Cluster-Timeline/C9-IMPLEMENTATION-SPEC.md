# C9 Cluster Timeline Implementation Spec

**Reference Prototype**: `5-variants-C9.qml`

This spec captures all implementation details for integrating C9 into LearnView.qml.

## File to Modify

`familydiagram/pkdiagram/resources/qml/Personal/LearnView.qml`

## Key Features from C9

1. **Pattern legend** at top showing all 5 SARF patterns
2. **Stacked cluster bars** (3 rows) positioned by date range
3. **Pinch-to-zoom** (1x to 5x) - horizontal only
4. **Wheel/drag to pan** when zoomed
5. **Always-visible text** in bars (elided when small)
6. **Selection glow** on selected cluster
7. **Scroll indicator** showing viewport position
8. **Reset button** when zoomed

## Implementation Changes

### 1. Add zoom/pan properties (near existing properties ~line 50)

```qml
property real timelineZoom: 1.0
property real timelineScrollX: 0
property real minZoom: 1.0
property real maxZoom: 5.0
```

### 2. Add pattern legend row (above mini-graph)

```qml
Row {
    x: graphPadding + 4
    y: miniGraphY - 16
    spacing: 8
    visible: showClusters && !isFocused && clusterModel && clusterModel.hasClusters

    Repeater {
        model: [
            {pattern: "anxiety_cascade", label: "Anxiety"},
            {pattern: "triangle_activation", label: "Triangle"},
            {pattern: "conflict_resolution", label: "Conflict"},
            {pattern: "reciprocal_disturbance", label: "Disturb"},
            {pattern: "functioning_gain", label: "Gain"}
        ]
        Row {
            spacing: 3
            Rectangle { width: 6; height: 6; radius: 3; color: patternColor(modelData.pattern) }
            Text { text: modelData.label; font.pixelSize: 8; color: "#606070" }
        }
    }
}
```

### 3. Add PinchArea wrapping graph content

```qml
MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.NoButton
    visible: showClusters && !isFocused
    onWheel: {
        var deltaX = wheel.angleDelta.x !== 0 ? wheel.angleDelta.x : wheel.angleDelta.y
        var maxScroll = Math.max(0, gWidth * timelineZoom - gWidth)
        timelineScrollX = Math.max(0, Math.min(timelineScrollX - deltaX * 0.5, maxScroll))
        wheel.accepted = true
    }
}

PinchArea {
    id: clusterPinchArea
    anchors.fill: parent
    enabled: showClusters && !isFocused

    property real startZoom: 1.0
    property real startScrollX: 0
    property point startCenter: Qt.point(0, 0)

    onPinchStarted: {
        startZoom = timelineZoom
        startScrollX = timelineScrollX
        startCenter = pinch.center
    }

    onPinchUpdated: {
        var newZoom = Math.max(minZoom, Math.min(maxZoom, startZoom * pinch.scale))
        var baseWidth = gWidth
        var newContentWidth = baseWidth * newZoom
        var pinchXRatio = (startCenter.x - gLeft + startScrollX) / (baseWidth * startZoom)
        var newScrollX = pinchXRatio * newContentWidth - (startCenter.x - gLeft)
        var maxScroll = Math.max(0, newContentWidth - baseWidth)
        timelineScrollX = Math.max(0, Math.min(newScrollX, maxScroll))
        timelineZoom = newZoom
    }
}
```

### 4. Add xPosZoomed() function for zoomed coordinates

```qml
function xPosZoomed(year) {
    if (!showClusters || isFocused) return xPos(year)
    var yearStart = clusterMinYearFrac
    var yearSpan = clusterYearSpan
    if (yearSpan === 0) yearSpan = 1
    var baseX = ((year - yearStart) / yearSpan) * gWidth
    return gLeft + baseX * timelineZoom - timelineScrollX
}
```

### 5. Replace cluster carousel with C9-style stacked bars

```qml
Repeater {
    model: showClusters && !isFocused && clusterModel ? clusterModel.clusters : []

    Rectangle {
        objectName: "clusterBar_" + index
        property real startYear: dateToYearFrac(modelData.startDate) || clusterMinYearFrac
        property real endYear: dateToYearFrac(modelData.endDate) || clusterMaxYearFrac
        property int row: index % 3
        property bool isSelected: selectedClusterIndex === index

        x: xPosZoomed(startYear)
        y: miniGraphY + 8 + row * 34
        width: Math.max(20, xPosZoomed(endYear) - xPosZoomed(startYear))
        height: 28
        radius: 4
        color: patternColor(modelData.pattern)
        opacity: isSelected ? 1.0 : 0.7
        clip: true
        visible: x + width > gLeft && x < gRight

        Rectangle {
            anchors.fill: parent
            anchors.margins: -4
            radius: 8
            color: "transparent"
            border.color: patternColor(modelData.pattern)
            border.width: 2
            opacity: 0.6
            visible: isSelected
        }

        Text {
            anchors.centerIn: parent
            text: modelData.title
            font.pixelSize: 9
            font.bold: true
            color: "white"
            elide: Text.ElideRight
            width: Math.max(0, parent.width - 6)
            horizontalAlignment: Text.AlignHCenter
        }

        MouseArea {
            anchors.fill: parent
            onClicked: focusCluster(index)
        }
    }
}
```

### 6. Add drag-to-pan background handler

```qml
MouseArea {
    anchors.fill: parent
    z: -1
    enabled: showClusters && !isFocused

    property real dragStartX: 0
    property real dragStartScrollX: 0
    property bool isDragging: false

    onPressed: { dragStartX = mouse.x; dragStartScrollX = timelineScrollX; isDragging = false }
    onPositionChanged: {
        if (pressed && Math.abs(mouse.x - dragStartX) > 5) {
            isDragging = true
            var maxScroll = Math.max(0, gWidth * timelineZoom - gWidth)
            timelineScrollX = Math.max(0, Math.min(dragStartScrollX + dragStartX - mouse.x, maxScroll))
        }
    }
    onReleased: if (!isDragging) selectedClusterIndex = -1
}
```

### 7. Add scroll indicator and reset button

```qml
Rectangle {
    anchors.bottom: miniGraphArea.bottom
    anchors.bottomMargin: 2
    anchors.horizontalCenter: miniGraphArea.horizontalCenter
    width: gWidth * 0.6; height: 3; radius: 1.5
    color: "#1a1a2a"
    visible: showClusters && !isFocused && timelineZoom > 1.05

    Rectangle {
        x: parent.width * (timelineScrollX / (gWidth * timelineZoom))
        width: Math.max(16, parent.width / timelineZoom)
        height: parent.height; radius: parent.radius
        color: "#505060"
    }
}

Rectangle {
    anchors.right: parent.right
    anchors.rightMargin: graphPadding
    y: miniGraphY
    width: 40; height: 18; radius: 9
    color: "#3a3a4a"
    visible: showClusters && !isFocused && timelineZoom > 1.05

    Text { anchors.centerIn: parent; text: "Reset"; font.pixelSize: 9; color: "#ffffff" }
    MouseArea { anchors.fill: parent; onClicked: { timelineZoom = 1.0; timelineScrollX = 0 } }
}
```

### 8. Reset zoom on focus/unfocus

In `focusCluster()` and `clearFocus()`:
```qml
timelineZoom = 1.0
timelineScrollX = 0
```

## Pattern Colors (from C9)

```qml
function patternColor(pattern) {
    switch (pattern) {
        case "anxiety_cascade": return "#e74c3c"
        case "triangle_activation": return "#9b59b6"
        case "conflict_resolution": return "#27ae60"
        case "reciprocal_disturbance": return "#e67e22"
        case "functioning_gain": return "#3498db"
        default: return "#909098"
    }
}
```

## Verification Checklist

1. **Launch Personal app** with test data containing clusters
2. **Clusters toggle ON**:
   - Pattern legend visible at top
   - Cluster bars in 3 rows by date range
   - Text always visible (elided when small)
3. **Pinch-zoom**: Bars stretch horizontally
4. **Pan**: Wheel scroll or drag to pan when zoomed
5. **Selection**: Tap shows glow, click focuses cluster
6. **Reset button**: Returns to 1x zoom
7. **Focus mode**: Events and SARF lines display correctly
