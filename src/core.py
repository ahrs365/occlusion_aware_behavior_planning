import numpy as np

from environment import Environment
from pose import Pose, VehicleDynamic
from ego_car import EgoVehicle
from objects import Vehicle, Pedestrian
import _param as param


class Core(object):

    def __init__(self):
        self._egoCar = None
        self._env = Environment()
        self.timestamp_s = 0

    """ Run functions """

    def move(self, dT=param._dT):
        if (self._egoCar is not None and
           self.timestamp_s + dT <= param._SIMULATION_TIME):
            self._egoCar.optimize()
            self._env.move(currentTime=self.timestamp_s)
            self.timestamp_s = round(self.timestamp_s + dT, 3)
            return True
        else:
            return False

    def reset(self):
        self._egoCar = None
        self._env = Environment()
        self.timestamp_s = 0

    def getTimeParameter(self, dT, simulationTime, predictTime):
        param._dT = dT
        param._SIMULATION_TIME = simulationTime
        param._PREDICT_TIME = predictTime

    def getCurrentTime(self):
        return self.timestamp_s

    def getSimulationTime(self):
        return param._SIMULATION_TIME

    """ Add elements functions """

    def addEgoVehicle(self, length, width, x_m, y_m, theta, cov_long, cov_lat,
                      vx_ms, u_in, startTime):

        startPose = Pose(
            x_m=x_m, y_m=y_m, yaw_rad=theta,
            covLatLong=np.diag([cov_long, cov_lat]),
            vdy=VehicleDynamic(vx_ms, 0), timestamp_s=startTime)
        self._egoCar = EgoVehicle(
            length=length, width=width, env=self._env,
            startPose=startPose, u_in=u_in)
        print("Ego vehicle added.")

    def addOtherVehicle(self, length, width, x_m, y_m, to_x_m, to_y_m,
                        cov_long, cov_lat, vx_ms, startTime, isStop=False):

        otherCar = Vehicle(
            idx=self._env.countVehicle()+1,
            length=length, width=width,
            from_x_m=x_m, from_y_m=y_m,
            to_x_m=to_x_m, to_y_m=to_y_m,
            covLong=cov_long, covLat=cov_lat,
            vx_ms=vx_ms, startTime=startTime, isStop=isStop)
        self._env.addVehicle(otherCar)
        print("Vehicle count: {:}".format(self._env.countVehicle()))

    def addPedestrian(self, x_m, y_m, to_x_m, to_y_m,
                      cov_long, cov_lat, vx_ms, startTime, isStop=False):

        pedestrian = Pedestrian(
            idx=self._env.countPedestrian()+1,
            from_x_m=x_m, from_y_m=y_m,
            to_x_m=to_x_m, to_y_m=to_y_m,
            covLong=cov_long, covLat=cov_lat,
            vx_ms=vx_ms, startTime=startTime, isStop=isStop)
        self._env.addPedestrian(pedestrian)
        print("Pedestrian count: {:}".format(self._env.countPedestrian()))

    def addStaticObject(self, staticObject):
        self._env.addStaticObject(staticObject)

    """ Export functions """

    # ego vehicle

    def getCurrentEgoPoly(self):
        if self._egoCar is None:
            return None
        return self._egoCar.getCurrentPoly()

    def getCurrentEgoPos(self):
        if self._egoCar is None:
            return None
        return [self._egoCar.getCurrentPose().x_m,
                self._egoCar.getCurrentPose().y_m]

    def getCurrentFOV(self):
        if self._egoCar is None:
            return None
        return self._egoCar._fov

    def getCurrentVelocity(self):
        if self._egoCar is None:
            return None
        return self._egoCar.getCurrentLongtitudeVelocity()

    def getCurrentAcceleration(self):
        if self._egoCar is None:
            return None
        return self._egoCar.getCurrentLongtitudeAcceleration()

    # environment

    def exportCurrentPedestrian(self):
        pedesList = []
        for pedes in self._env._l_pedestrian:
            if pedes.getCurrentTimestamp() == self.timestamp_s:
                pedesExport = pedes.exportCurrent()
                pedesList.append(pedesExport)
        return pedesList

    def exportCurrentVehicle(self):
        vehList = []
        for vehicle in self._env._l_vehicle:
            if vehicle.getCurrentTimestamp() == self.timestamp_s:
                vehExport = vehicle.exportCurrent()
                vehList.append(vehExport)
        return vehList

    def exportHypoPedestrian(self):
        hypoList = []
        for pedes in self._env._l_hypoPedes:
            pedesExport = pedes.exportCurrent()
            hypoList.append(pedesExport)
        return hypoList

    def exportHypoVehicle(self):
        hypoList = []
        for veh in self._env._l_hypoVehicle:
            vehExport = veh.exportCurrent()
            hypoList.append(vehExport)
        return hypoList

    def plotDynamic(self):
        if self._egoCar is None:
            return
        self._egoCar.plotDynamic()

    def plotDynamicDistance(self):
        if self._egoCar is None:
            return
        self._egoCar.plotDynamicDistance()

    def plotRisk(self):
        if self._egoCar is None:
            return
        self._egoCar.plotPassedCost()

    def restart(self):
        if self._egoCar is None:
            return
        self.timestamp_s = 0
        self._egoCar.restart()
        self._env.restart()

    def replay(self):
        if self._egoCar is None:
            return
        # bool for replay