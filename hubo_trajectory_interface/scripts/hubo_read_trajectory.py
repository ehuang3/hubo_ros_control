#!/usr/bin/env python
# Jim Mainprice WPI, august 2013

import rospy;
import roslib;
roslib.load_manifest('hubo_trajectory_interface')

from math import *
import random
import time

# Brings in the SimpleActionClient
import actionlib

from std_msgs.msg import String
from hubo_robot_msgs.msg import *
from trajectory_msgs.msg import JointTrajectoryPoint

from copy import deepcopy
import sys

class TrajectoryReader():

    def __init__( self, robot_name, joint_mapping ):
        
        self.robot_name = robot_name
        self.joint_mapping = joint_mapping
        self.hubo_traj = None
        self.dt = 0.05 # 20 Hz

        # Ach trajectory mapping. This mapping differs from the internal ros mapping
        # which is defined as a global parameter (joints) in the parameter server   
        self.hubo_ach_traj_joint_names = {       0 : 'RHY' ,  1 : 'RHR' ,  2 : 'RHP' ,  3 : 'RKN' ,  4 :  'RAP' ,  
                                                 5 : 'RAR' ,  6 : 'LHY' ,  7 : 'LHR' ,  8 : 'LHP' ,  9 : 'LKN' , 
                                                10 : 'LAP' , 11 : 'LAR' , 12 : 'RSP' , 13 : 'RSR' , 14 : 'RSY' , 
                                                15 : 'REB' , 16 : 'RWY' , 17 : 'RWR' , 18 : 'RWP' , 19 : 'LSP' , 
                                                20 : 'LSR' , 21 : 'LSY' , 22 : 'LEB' , 23 : 'LWY' , 24 : 'LWR' , 
                                                25 : 'LWP' , 26 : 'NKY' , 27 : 'NK1' , 28 : 'NK2' , 29 : 'WST' ,
                                                30 : 'RF1' , 31 : 'RF2' , 32 : 'RF3' , 33 : 'RF4' , 34 : 'RF5' ,  
                                                35 : 'LF1' , 36 : 'LF2' , 37 : 'LF3' , 38 : 'LF4' , 39 : 'LF5' }
        return
    

    # Load file and store in a ROS message type
    # return False if the trajectory could not be loaded
    def loadfile(self,fname):

        print "parsing file"

        # open the file and reads the array
        f = open(fname,'r')
        array = []
        for line in f:
            array.append([float(x) for x in line.split()])
        f.close()

        if( len(array) == 0 ):
            print "Warning : empty trajectory"
            return False

        print "filing message"

        self.hubo_traj = JointTrajectory()
        self.hubo_traj.header.stamp = rospy.Time.now()

        t = 0.0

        for line in array: # read all lines in file

            # Ane configuration per line
            current_point = JointTrajectoryPoint()
            current_point.time_from_start = rospy.Duration(t)

            # Advance in time by dt
            t += self.dt

            # ---------------------------------------
            # Fill position buffers
            p_buffer = []
            for p in range( len(line) ):

                try:
                    i = self.joint_mapping[ self.hubo_ach_traj_joint_names[p] ]
                except KeyError:
                    i = None
                if i is not None:
                    p_buffer.append(float(line[i]))

            # ---------------------------------------
            # Fill velocity buffers using finite defercing
            v_buffer = []
            v_buffer.append( (p_buffer[0]-p_buffer[1])/self.dt )
            for i in range( 1 , len(p_buffer)-1 ):
                v_buffer.append( (p_buffer[i+1]-p_buffer[i-1])/self.dt )
            v_buffer.append( (p_buffer[len(p_buffer)-1]-p_buffer[len(p_buffer)-2])/self.dt )

            # ---------------------------------------
            # Fill acceleration buffers using finite defercing
            a_buffer = []
            a_factor = 10;
            a_buffer.append( a_factor*(v_buffer[0]-v_buffer[1])/self.dt )
            for i in range( 1 , len(v_buffer)-1 ):
                a_buffer.append( a_factor*(v_buffer[i+1]-v_buffer[i-1])/self.dt )
            a_buffer.append( a_factor*(v_buffer[len(v_buffer)-1]-v_buffer[len(v_buffer)-2])/self.dt )

            # Append trajectory point
            current_point.positions = deepcopy(p_buffer)
            current_point.velocities = deepcopy(v_buffer)
            current_point.accelerations = deepcopy(a_buffer)

            self.hubo_traj.points.append(current_point)
        
        return True


    # Sends the trajectory the actionLib
    # returns when the trajectory is finished exected
    def execute(self):

        if( self.hubo_traj is None ):
            print "cannot execute empty trajectory"
            return

        # Creates a SimpleActionClient, passing the type of the action to the constructor.
        client = actionlib.SimpleActionClient('/drchubo_fullbody_controller/joint_trajectory_action', hubo_robot_msgs.msg.JointTrajectoryAction )
        

        # Waits until the action server has start
        print "waiting for action server..."
        client.wait_for_server()
        
        # Execute the start
        print "client started, sending trajectory!"
        res = None
        rospy.sleep(1.0)
        traj_goal = JointTrajectoryGoal()
        traj_goal.trajectory = self.hubo_traj
        traj_goal.trajectory.header.stamp = rospy.Time.now()
        client.send_goal( traj_goal )
        client.wait_for_result()
        res = client.get_result()
        print res

        return

if __name__ == "__main__":
    # This script presents the same interface as the huo-read-trajectory program
    # one can run this script from terminal passing the frequency
    # and the compliance mode
    file_name = None
    compliance = False
    frequency = False
    play = False

    accepted_freq = [100, 50, 25, 10, 200, 500]

    if(len(sys.argv) >= 2):

        for index in range(1,len(sys.argv)):

            if(sys.argv[index] == "-n" and index+1<len(sys.argv)):
                file_name = sys.argv[index+1]
                play = True
                try:
                    with open(file_name): pass
                except IOError:
                    play = False
                    print "file :" + file_name + " does not exist"

            elif(sys.argv[index] == "-f" and index+1<len(sys.argv)):
                frequency = int(sys.argv[index+1])
                if( frequency in accepted_freq ):
                    play = True
                else:
                    print "frequency is not in accepted"
                    print accepted_freq
                    play = True

    if not play:
        print "error in arguments!!!"

    else: # All arguments are fine, play trajectory

        rospy.init_node( "hubo_read_trajectory" )

        # Hard coded namespace
        robot_name = "drchubo"
        ns = "/" + robot_name + "_fullbody_controller/hubo_trajectory_action/"

        # Get joint mapping from parameter server
        joint_names = rospy.get_param( ns + "joints")
        joint_mapping = {}
        for i in range(0,len(joint_names)):
            joint_names[i] = joint_names[i].strip( '/' )
            joint_mapping[ joint_names[i] ] = int(i)
            
        print joint_mapping

        # Load and execute trajectory through actionLib
        reader = TrajectoryReader( robot_name, joint_mapping )
        if reader.loadfile( file_name ):
            reader.execute()
            print "done!"
        else:
            print "Could not load trajectory"

