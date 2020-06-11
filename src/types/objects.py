from matplotlib.patches import Ellipse, Polygon
import math
import numpy as np
import matplotlib.pyplot as plt

from pose import Pose, VehicleDynamic
import pose_functions as pfnc
import _param as param


class StaticObject(object):
    """
        Class define static object as polygon
        Param: UTM coordinate
            _idx: index of object
            _poly: (n,2) array vertices of object polygon
    """
    def __init__(self, idx, poly):
        self._idx = idx
        self._poly = poly
        self._center = np.mean(poly, axis=0)


class Road(object):
    def __init__(self, left, right, lane, prior=False):
        self.left = left
        self.right = right
        self.lane = lane
        self.theta = math.atan2(left[1][1]-left[0][1], left[1][0]-left[0][0])


class PedestrianCross(object):

    def __init__(self, left, right, density):
        assert np.linalg.norm(left[0] - left[1]) == \
               np.linalg.norm(right[0] - right[1])
        self.left = left
        self.right = right
        self.center = 0.5*(np.mean(left, axis=0) + np.mean(right, axis=0))
        self.theta = math.atan2(left[1][1]-left[0][1], left[1][0]-left[0][0])


class Vehicle(object):

    def __init__(self, idx, length, width,
                 from_x_m, from_y_m, to_x_m, to_y_m,
                 covLong, covLat, vx_ms, startTime, isStop=False,
                 appearRate=1, interactRate=1, dT=param._dT):
        self._idx = idx
        self._length = length
        self._width = width

        startTime = round(round(startTime/dT, 2) * dT, 2)
        self._startTime = startTime
        self.theta = math.atan2(to_y_m-from_y_m, to_x_m-from_x_m)
        startPose = Pose(
            x_m=from_x_m, y_m=from_y_m, yaw_rad=self.theta,
            covLatLong=np.diag([covLong, covLat]),
            vdy=VehicleDynamic(vx_ms, 0), timestamp_s=startTime)

        if isStop:
            self._u = pfnc.computeAccToStop(
                from_x_m=from_x_m, from_y_m=from_y_m,
                to_x_m=to_x_m, to_y_m=to_y_m, vx_ms=vx_ms)
        else:
            self._u = 0

        self._p_pose = {}
        self._isDetected = False
        self._appearRate = appearRate
        self._Pcoll = 0
        self._currentPose = startPose
        self._l_pose = {startPose.timestamp_s: startPose}
        # for hypothetical object
        self._interactRate = interactRate

    def isVisible(self):
        return self._isDetected

    def setDetected(self, a0: bool):
        self._isDetected = a0

    def setCollisionProb(self, a: float):
        self._Pcoll = max(self._Pcoll, a, 1)

    def getCurrentPose(self):
        return self._currentPose

    def getCurrentTimestamp(self):
        return self._currentPose.timestamp_s

    def getPoseAt(self, timestamp_s: float):
        if timestamp_s not in self._l_pose:
            return None
        else:
            return self._l_pose[timestamp_s]

    def getPoly(self, timestamp_s: float):
        """
        Return the bounding polygon of vehicle
        """
        pose = self.getPoseAt(timestamp_s)
        if pose is None:
            return None
        return pfnc.rectangle(pose, self._length, self._width)

    def getCurrentPoly(self):
        return pfnc.rectangle(self._currentPose, self._length, self._width)

    def predict(self, const_vx=False, dT=param._PREDICT_STEP,
                pT=param._PREDICT_TIME):
        """
        Predict the vehicle motion from current state
        Args:
            const_vx: if True predict with constant velocity
                      else with current acceleration
        """
        self._p_pose = {}
        nextTimestamp_s = self.getCurrentTimestamp() + pT
        if const_vx:
            self._p_pose = pfnc.updatePoseList(
                lastPose=self._currentPose,
                u_in=0,
                nextTimestamp_s=nextTimestamp_s,
                dT=dT
            )
        else:
            self._p_pose = pfnc.updatePoseList(
                lastPose=self._currentPose,
                u_in=self._u,
                nextTimestamp_s=nextTimestamp_s,
                dT=dT
            )

    def getPredictAt(self, timestamp_s: float):
        timestamp_s = round(timestamp_s, 2)
        if timestamp_s not in self._p_pose:
            self.predict(dT=param._PREDICT_STEP, pT=param._PREDICT_TIME)
        pose = self._p_pose[timestamp_s]
        posePoly = pfnc.rectangle(pose, self._length, self._width)
        return pose, posePoly

    def move(self, dT=param._dT):
        """
        Update vehicle state to next timestamp
        """
        lastPose = self.getCurrentPose()
        nextTimestamp_s = round(lastPose.timestamp_s + dT, 2)
        nextPose = pfnc.updatePose(
            lastPose=lastPose,
            u_in=self._u,
            dT=dT
            )
        self._currentPose = nextPose
        self._l_pose.update({nextTimestamp_s: nextPose})

    def restart(self):
        t = min(self._l_pose)
        firstPose = self._l_pose[t]
        self._l_pose = {t: firstPose}
        self._currentPose = firstPose
        self._p_pose = {}

    # -------------------- Export functions -----------------------------------

    def exportCurrent(self):
        cPose = self._currentPose
        exportVehicle = {
            'pos': [cPose.x_m, cPose.y_m, cPose.yaw_rad],
            'cov': cPose.covLatLong,
            'poly': self.getCurrentPoly(),
            'visible': self.isVisible(),
            'Pcol': self._Pcoll
            }
        return exportVehicle

    def exportPredictState(self):
        l_p = []
        self._p_pose.keys()
        for p_pose in self._p_pose:
            exportP = {
                'pos': [p_pose.x_m, p_pose.y_m, p_pose.yaw_rad],
                'cov': p_pose.covLatLong,
                'poly': pfnc.rectangle(p_pose, self._length, self._width),
            }
            l_p.append(exportP)
        return l_p


class Pedestrian(object):

    def __init__(self, idx, from_x_m, from_y_m, to_x_m, to_y_m,
                 covLong, covLat, vx_ms, startTime, isStop=False,
                 appearRate=1, interactRate=1, dT=param._dT):
        self._idx = idx
        self._length = 1.5
        self._width = 1.5

        startTime = round(round(startTime/dT, 2) * dT, 2)
        self._startTime = startTime
        self.theta = math.atan2(to_y_m-from_y_m, to_x_m-from_x_m)
        startPose = Pose(
            x_m=from_x_m, y_m=from_y_m, yaw_rad=self.theta,
            covLatLong=np.diag([covLong, covLat]),
            vdy=VehicleDynamic(vx_ms, 0), timestamp_s=startTime)

        if isStop:
            s = np.sqrt((from_x_m-to_x_m)**2 + (from_y_m-to_y_m)**2)
            self._stopTimestamp_s = startTime + s / vx_ms
        else:
            self._stopTimestamp_s = 99999

        self._u = 0
        self._isDetected = False
        self._appearRate = appearRate
        self._p_pose = {}
        self._Pcoll = 0
        self._currentPose = startPose
        self._l_pose = {startPose.timestamp_s: startPose}
        # for hypothetical objects
        self._interactRate = interactRate

    def isVisible(self):
        return self._isDetected

    def setDetected(self, a0: bool):
        self._isDetected = a0

    def setCollisionProb(self, a: float):
        self._Pcoll = max(self._Pcoll, a, 1)

    def getCurrentPose(self):
        return self._currentPose

    def getCurrentTimestamp(self):
        return self._currentPose.timestamp_s

    def getPoseAt(self, timestamp_s: float):
        if timestamp_s not in self._l_pose:
            return None
        else:
            return self._l_pose[timestamp_s]

    def getPoly(self, timestamp_s: float):
        """
        Return the bounding polygon of vehicle
        """
        pose = self.getPoseAt(timestamp_s)
        if pose is None:
            return None
        return pfnc.rectangle(pose, self._length, self._width)

    def getCurrentPoly(self):
        return pfnc.rectangle(self._currentPose, self._length, self._width)

    def predict(self, dT=param._PREDICT_STEP, pT=param._PREDICT_TIME):
        """
        Predict the vehicle motion from current state
        Args:
            const_vx: if True predict with constant velocity
                      else with current acceleration
        """
        self._p_pose = {}
        nextTimestamp_s = self.getCurrentTimestamp() + pT
        self._p_pose = pfnc.updatePoseList(
            lastPose=self._currentPose,
            u_in=self._u,
            nextTimestamp_s=nextTimestamp_s,
            dT=dT
        )

    def getPredictAt(self, timestamp_s: float):
        timestamp_s = round(timestamp_s, 2)
        if timestamp_s not in self._p_pose:
            self.predict(dT=param._PREDICT_STEP, pT=param._PREDICT_TIME)
        pose = self._p_pose[timestamp_s]
        posePoly = pfnc.rectangle(pose, self._length, self._width)
        return pose, posePoly

    def move(self, dT=param._dT):
        """
        Update vehicle state to next timestamp
        """
        lastPose = self.getCurrentPose()
        nextTimestamp_s = round(lastPose.timestamp_s + dT, 2)
        if nextTimestamp_s < self._stopTimestamp_s:
            nextPose = pfnc.updatePose(
                lastPose=lastPose,
                u_in=self._u,
                dT=dT
                )
        else:
            nextPose = Pose(
                x_m=lastPose.x_m, y_m=lastPose.y_m, yaw_rad=lastPose.yaw_rad,
                covLatLong=lastPose.covLatLong, vdy=VehicleDynamic(0, 0),
                timestamp_s=nextTimestamp_s)
        self._currentPose = nextPose
        self._l_pose.update({nextTimestamp_s: nextPose})

    def restart(self):
        t = min(self._l_pose)
        firstPose = self._l_pose[t]
        self._l_pose = {t: firstPose}
        self._currentPose = firstPose
        self._p_pose = {}

    # -------------------- Export functions -----------------------------------

    def exportCurrent(self):
        cPose = self._currentPose
        exportPedes = {
            'pos': [cPose.x_m, cPose.y_m, cPose.yaw_rad],
            'cov': cPose.covLatLong,
            'poly': self.getCurrentPoly(),
            'visible': self.isVisible(),
            'Pcoll': self._Pcoll,
            }
        return exportPedes

    def exportPredictState(self):
        l_p = []
        self._p_pose.keys()
        for p_pose in self._p_pose:
            exportP = {
                'pos': [p_pose.x_m, p_pose.y_m, p_pose.yaw_rad],
                'cov': p_pose.covLatLong,
                'poly': pfnc.rectangle(p_pose, self._length, self._width),
            }
            l_p.append(exportP)
        return l_p
