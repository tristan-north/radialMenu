from canvaseventtypes import *

w = None

def createEventHandler(uievent, pending_actions):
    if isinstance(uievent, KeyboardEvent) and uievent.eventtype == 'keyhit' and uievent.key == 'Shift+Tab':

        context = uievent.editor.pwd().childTypeCategory()
        contextLabel = context.label()

        otlsList = []

        if contextLabel == 'Geometry':
            otlsList = ['null', 'xform', 'blast', 'split', 'attribwrangle', 'attribvop', 'object_merge', 'merge']

        elif contextLabel == 'Objects':
            otlsList = ['null', '', 'hlight', '', 'cam', '', 'geo', '']

        elif contextLabel == 'Outputs':
            otlsList = ['null', '', '', '', '', 'fetch', 'ifd', 'merge']

        elif contextLabel == 'VEX Builder':
            otlsList = ['aanoise', 'fit', 'bind', 'add', 'multiply', 'rampparm', 'vectofloat', 'floattovec']

        else:
            return None, False

        global w
        w = RadialWin(uievent.editor, otlsList, context)

        # We handled this event, but don't need to return an event handler
        # because this is a one-off event. We don't care what happens next.
        return None, True

    return None, False



def findLatestTypeVersion(versionlessType, context):
    nodeTypes = context.nodeTypes()

    latest = None
    latestVer = 0.0
    for nodeType in nodeTypes.keys():
        if not nodeType.startswith(versionlessType): continue
        
        split = nodeType.split('::')
        if float(split[3]) > latestVer:
            latest = nodeType
            latestVer = float(split[3])

    return latest



from PySide2 import QtCore, QtWidgets, QtGui
import hou, toolutils
import math


class RadialWin(QtWidgets.QFrame):
    def __init__(self, networkEditor, otlsList, context):
        self.networkEditor = networkEditor
        self.numSegments = 8
        self.iconSize = 23
        self.innerCircleRadius = 60
        self.outerCircleRadius = 120
        self.otlsList = otlsList

        QtWidgets.QFrame.__init__(self, None)

        pos = QtGui.QCursor.pos()
        self.setGeometry(pos.x()-self.outerCircleRadius, pos.y()-self.outerCircleRadius, self.outerCircleRadius*2+2, self.outerCircleRadius*2+2)
        self.setWindowFlags(QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True);
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)  # Since it has no parent this will clean up when it closes
        self.setMouseTracking(True)
        self.mousePos = QtCore.QPoint(0,0)

        self.radialGrad = QtGui.QRadialGradient(QtCore.QPoint(self.width()/2, self.height()/2), self.outerCircleRadius)
        self.radialGrad.setColorAt(0, QtGui.QColor(35,35,35, 240))
        self.radialGrad.setColorAt(1, QtGui.QColor(40,40,40, 240))

        self.radialGradHighlighted = QtGui.QRadialGradient(self.radialGrad)
        self.radialGradHighlighted.setColorAt(0, QtGui.QColor(40,40,40, 240))
        self.radialGradHighlighted.setColorAt(1, QtGui.QColor(50,50,50, 240))

        # Build gui elements
        self.font = QtGui.QFont('Arial', 7)
        self.center = QtCore.QPoint(self.width()/2, self.height()/2)
        innerCirclePath = QtGui.QPainterPath()
        innerCirclePath.addEllipse(self.center, self.innerCircleRadius, self.innerCircleRadius)
        self.segments = []

        rot = 360.0 / self.numSegments
        for i in xrange(self.numSegments):
            seg = QtGui.QPainterPath()
            seg.moveTo(self.center)
            seg.arcTo(self.rect() + QtCore.QMargins(-1,-1,-1,-1), 112.5 + i*rot, -rot)
            seg = seg.subtracted(innerCirclePath)

            seg.otlName = self.otlsList[i]
            if seg.otlName.startswith('lfl::'):
                seg.nodeType = hou.nodeType(context, findLatestTypeVersion(seg.otlName, context))
            else:
                seg.nodeType = hou.nodeType(context, seg.otlName)

            if seg.otlName != '':
                iconName = seg.nodeType.icon()
                seg.icon = hou.qt.Icon(iconName).pixmap(self.iconSize, self.iconSize)

                seg.staticText = QtGui.QStaticText(hou.hda.componentsFromFullNodeTypeName(seg.otlName)[2])
                seg.staticText.prepare(font=self.font)

                textX = self.center.x() + math.sin(i*math.radians(rot)+math.pi) * (self.innerCircleRadius+self.outerCircleRadius)/2
                textY = self.center.y() + math.cos(i*math.radians(rot)+math.pi) * (self.innerCircleRadius+self.outerCircleRadius)/2
                seg.center = QtCore.QPoint(textX, textY)
                textX -= seg.staticText.size().width()/2
                textY -= seg.staticText.size().height()/2
                seg.textDrawPos = QtCore.QPoint(textX, textY)


            self.segments.append(seg)


        self.show()


    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.close()

            for seg in self.segments:
                if seg.contains(event.pos()) and seg.otlName != '':
                    toolutils.genericTool({'pane':self.networkEditor}, seg.nodeType.name())
                    break

    def mouseMoveEvent(self, event):
        self.mousePos = event.pos()
        self.update()


    def leaveEvent(self, event):
        #self.close()
        pass

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        
        painter.setPen(QtGui.QColor(110, 110, 110, 200))

        for seg in self.segments:
            # Figure out if cursor is in segment
            if seg.contains(self.mousePos) and seg.otlName != '':
                painter.setBrush(self.radialGradHighlighted)
            else:
                painter.setBrush(self.radialGrad)

            painter.drawPath(seg)

        painter.setPen(QtGui.QColor(140, 140, 140))
        painter.setFont(self.font)

        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceAtop)
        for seg in self.segments:
            if seg.otlName == '': continue

            painter.drawPixmap(seg.center - QtCore.QPoint(self.iconSize/2, self.iconSize/2+3), seg.icon)
            painter.drawStaticText(seg.textDrawPos.x(), seg.textDrawPos.y()+14, seg.staticText)

        painter.end()
