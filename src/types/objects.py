from matplotlib.patches import Ellipse, Polygon
import matplotlib.pyplot as plt

from pose import Pose, VehicleDynamic
import numpy as np
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

    def plot(self, ax=plt):
        poly = Polygon(
            self._poly, facecolor='gray',
            edgecolor='black', alpha=1, label='static object'
            )
        ax.add_patch(poly)


class RoadBoundary(object):
    """
        Class define road boundary as lines between points
        with UTM coordinate in ^-> direction
    """
    def __init__(self, scenario):
        self.left = None
        self.right = None
        self.lane = None
        self.setup(scenario)

    def setup(self, scenario):
        if scenario == 1:
            self.left = np.array([[[-100, 4], [100, 4]]])
            self.right = np.array([[[-100, -4], [100, -4]]])
            self.lane = np.array([[[-100, 0], [100, 0]]])

        if scenario == 2:
            self.left = np.array((
                [[-100, 4], [100, 4]],
                [[-4, -100], [-4, -4]]
            ))
            self.right = np.array((
                [[-100, -4], [-4, -4]],
                [[4, -4], [100, -4]],
                [[4, -100], [4, -4]]
            ))
            self.lane = np.array((
                [[-100, 0], [100, 0]],
                [[0, -100], [0, -4]]
            ))

        if scenario == 3:
            self.left = np.array((
                [[-100, 4], [-4, 4]],
                [[4, 4], [100, 4]],
                [[4, 100], [4, 4]],
                [[4, -100], [4, -4]]
            ))
            self.right = np.array((
                [[-100, -4], [-4, -4]],
                [[4, -4], [100, -4]],
                [[-4, 100], [-4, 4]],
                [[-4, -100], [-4, -4]]
            ))
            self.lane = np.array((
                [[-100, 0], [-4, 0]],
                [[4, 0], [100, -0]],
                [[0, 100], [0, 4]],
                [[0, -100], [0, -4]]
            ))

    def plot(self, ax=plt):
        nrRoad = self.lane.shape[0]
        for i in nrRoad:
            boundStyle = {'linestyle': '-', 'color': 'k'}
            plotLine(self.left[i], ax=ax, **boundStyle)
            plotLine(self.right[i], ax=ax, **boundStyle)
            laneStyle = {'linestyle': '--', 'color': 'k'}
            plotLine(self.lane[i], ax=ax, **laneStyle)


class Vehicle(object):

    def __init__(self, idx, length, width,
                 from_x_m, from_y_m, to_x_m, to_y_m,
                 covLong, covLat, vx_ms, startTime, isStop=False):
        self._idx = idx
        self._length = length
        self._width = width
        self._isDetected = False
        self._startTime = startTime
        self._p_pose = {}

        startTime = round(int(startTime/param._dT) * param._dT, 3)
        theta = np.arctan2(to_y_m-from_y_m, to_x_m-from_x_m)

        if isStop:
            self._u = pfnc.computeAccToStop(
                from_x_m=from_x_m, from_y_m=from_y_m,
                to_x_m=to_x_m, to_y_m=to_y_m, vx_ms=vx_ms)
        else:
            self._u = 0

        startPose = Pose(
            x_m=from_x_m, y_m=from_y_m, yaw_rad=theta,
            covLatLong=np.diag([covLong, covLat]),
            vdy=VehicleDynamic(vx_ms, 0), timestamp_s=startTime)

        self._currentPose = startPose
        self._l_pose = {startPose.timestamp_s: startPose}

    def isVisible(self):
        return self._isDetected

    def setDetected(self, a0: bool):
        self._isDetected = a0

    def getCurrentPose(self):
        return self._currentPose

    def getCurrentTimestamp(self):
        return self._currentPose.timestamp_s

    def getPoseAt(self, timestamp_s):
        if timestamp_s not in self._l_pose:
            return None
        else:
            return self._l_pose[timestamp_s]

    def predict(self, const_vx=False, pT=param._PREDICT_TIME):
        """
        Predict the vehicle motion from current state
        Args:
            const_vx: if True predict with constant velocity
                      else with current acceleration
        """
        self._p_pose = {}
        lastPose = self.getCurrentPose()
        nextTimestamp_s = self.getCurrentTimestamp() + pT
        if const_vx:
            self._p_pose = pfnc.updatePoseList(
                lastPose=lastPose,
                u_in=0,
                nextTimestamp_s=nextTimestamp_s
            )
        else:
            self._p_pose = pfnc.updatePoseList(
                lastPose=lastPose,
                u_in=self._u,
                nextTimestamp_s=nextTimestamp_s
            )

    def getPredictAt(self, timestamp_s):
        if timestamp_s not in self._p_pose:
            self.predict()
        pose = self._p_pose[timestamp_s]
        posePoly = pfnc.rectangle(pose.x_m, pose.y_m, pose.yaw_rad,
                                  self._length, self._width)
        return pose, posePoly
               
    def move(self, dT=param._dT):
        """
        Update vehicle state to next timestamp
        """
        lastPose = self.getCurrentPose()
        nextTimestamp_s = round(lastPose.timestamp_s + dT, 3)
        nextPose = pfnc.updatePose(
            lastPose=lastPose,
            u_in=self._u,
            dT=dT
            )
        self._currentPose = nextPose
        self._l_pose.update({nextTimestamp_s: nextPose})
        self._isDetected = False

    def getPoly(self, timestamp_s):
        """
        Return the bounding polygon of vehicle
        """
        pose = self.getPoseAt(timestamp_s)
        if pose is None:
            return None
        return pfnc.rectangle(pose.x_m, pose.y_m, pose.yaw_rad,
                              self._length, self._width)

    def plotAt(self, timestamp_s, ax=plt):
        if timestamp_s in self._l_pose:
            pose = self._l_pose[timestamp_s]
            ax.scatter(pose.x_m, pose.y_m, s=1, color='b')
            cov = pose.covLatLong
            ellipse = Ellipse([pose.x_m, pose.y_m],
                              width=np.sqrt(cov[0, 0])*2,
                              height=np.sqrt(cov[1, 1])*2,
                              angle=np.degrees(pose.yaw_rad),
                              facecolor=None,
                              edgecolor='blue',
                              alpha=0.4)
            ax.add_patch(ellipse)
        else:
            return

    def plot(self, maxTimestamp_s, ax=plt):
        for timestamp_s, pose in self._l_pose.items():
            if timestamp_s <= maxTimestamp_s:
                ax.scatter(pose.x_m, pose.y_m, s=1, color='b')
                cov = pose.covLatLong
                ellipse = Ellipse(
                    [pose.x_m, pose.y_m],
                    width=np.sqrt(cov[0, 0])*2,
                    height=np.sqrt(cov[1, 1])*2,
                    angle=np.degrees(pose.yaw_rad),
                    facecolor=None,
                    edgecolor='blue',
                    alpha=0.4)
                ax.add_patch(ellipse)
            if timestamp_s == maxTimestamp_s:
                poly = self.getPoly(timestamp_s)
                poly = Polygon(
                    poly, facecolor='cyan',
                    edgecolor='blue', alpha=0.7, label='other vehicle'
                )
                ax.add_patch(poly)


class Pedestrian(object):

    def __init__(self, idx, from_x_m, from_y_m, to_x_m, to_y_m,
                 covLong, covLat, vx_ms, startTime, isStop=False):
        self._idx = idx
        self._length = 1
        self._width = 1
        self._isDetected = False
        self._startTime = startTime
        self._u = 0
        self._p_pose = {}

        startTime = round(int(startTime/param._dT) * param._dT, 3)
        theta = np.arctan2(to_y_m-from_y_m, to_x_m-from_x_m)

        if isStop:
            s = np.sqrt((from_x_m-to_x_m)**2 + (from_y_m-to_y_m)**2)
            self._stopTimestamp_s = startTime + s / vx_ms
        else:
            self._stopTimestamp_s = 99999

        startPose = Pose(
            x_m=from_x_m, y_m=from_y_m, yaw_rad=theta,
            covLatLong=np.diag([covLong, covLat]),
            vdy=VehicleDynamic(vx_ms, 0), timestamp_s=startTime)

        self._currentPose = startPose
        self._l_pose = {startPose.timestamp_s: startPose}

    def isVisible(self):
        return self._isDetected

    def setDetected(self, a0: bool):
        self._isDetected = a0

    def getCurrentPose(self):
        return self._currentPose

    def getCurrentTimestamp(self):
        return self._currentPose.timestamp_s

    def getPoseAt(self, timestamp_s):
        if timestamp_s not in self._l_pose:
            return None
        else:
            return self._l_pose[timestamp_s]

    def predict(self, pT=param._PREDICT_TIME):
        """
        Predict the vehicle motion from current state
        Args:
            const_vx: if True predict with constant velocity
                      else with current acceleration
        """
        self._p_pose = {}
        lastPose = self.getCurrentPose()
        nextTimestamp_s = round(lastPose.timestamp_s + pT, 3)
        self._p_pose = pfnc.updatePoseList(
            lastPose=lastPose,
            u_in=self._u,
            nextTimestamp_s=nextTimestamp_s
        )

    def getPredictAt(self, timestamp_s):
        if timestamp_s not in self._p_pose:
            self.predict()
        pose = self._p_pose[timestamp_s]
        posePoly = pfnc.rectangle(pose.x_m, pose.y_m, pose.yaw_rad,
                                  self._length, self._width)
        return pose, posePoly

    def move(self, dT=param._dT):
        """
        Update vehicle state to next timestamp
        """
        lastPose = self.getCurrentPose()
        nextTimestamp_s = round(lastPose.timestamp_s + dT, 3)
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
        self._isDetected = False

    def getPoly(self, timestamp_s):
        """
        Return the bounding polygon of vehicle
        """
        pose = self.getPoseAt(timestamp_s)
        if pose is None:
            return None
        return pfnc.rectangle(pose.x_m,
                              pose.y_m,
                              pose.yaw_rad,
                              self._length,
                              self._width)

    def plotAt(self, timestamp_s, ax=plt):
        if timestamp_s in self._l_pose:
            pose = self._l_pose[timestamp_s]
            ax.scatter(pose.x_m, pose.y_m, s=1, color='b')
            cov = pose.covLatLong
            ellipse = Ellipse([pose.x_m, pose.y_m],
                              width=np.sqrt(cov[0, 0])*2,
                              height=np.sqrt(cov[1, 1])*2,
                              angle=np.degrees(pose.yaw_rad),
                              facecolor=None,
                              edgecolor='blue',
                              alpha=0.4)
            ax.add_patch(ellipse)
        else:
            return

    def plot(self, maxTimestamp_s, ax=plt):
        for timestamp_s, pose in self._l_pose.items():
            if timestamp_s <= maxTimestamp_s:
                ax.scatter(pose.x_m, pose.y_m, s=1, color='b')
                cov = pose.covLatLong
                ellipse = Ellipse(
                    [pose.x_m, pose.y_m],
                    width=np.sqrt(cov[0, 0])*2,
                    height=np.sqrt(cov[1, 1])*2,
                    angle=np.degrees(pose.yaw_rad),
                    facecolor=None,
                    edgecolor='blue',
                    alpha=0.4)
                ax.add_patch(ellipse)
            if timestamp_s == maxTimestamp_s:
                poly = self.getPoly(timestamp_s)
                poly = Polygon(
                    poly, facecolor='cyan',
                    edgecolor='blue', alpha=0.7, label='other vehicle'
                )
                ax.add_patch(poly)


def plotLine(line, ax=plt, **kwargs):
    ax.plot([line[0][0], line[1][0]], [line[0][1], line[1][1]], **kwargs)


class PedestrianCross(object):

    def __init__(self, left, right, density):
        assert np.linalg.norm(left[0] - left[1]) == \
               np.linalg.norm(right[0] - right[1])
        self.left = left
        self.right = right
        self.density = density
