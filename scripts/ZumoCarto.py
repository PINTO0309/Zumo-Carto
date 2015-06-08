#!/usr/bin/env python
# -*- coding: utf-8 -*-


import serial
from math import sqrt, cos, sin
import rospy
import tf
from time import sleep
from threading import Lock
from geometry_msgs.msg import Twist, Pose
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry



class Zumo:
    def __init__(self):
        self.DIAMETRE=0.038 #en metre
        self.ENTREAXE=0.084 #en metre
        self.COUNT=48
        self.temps=0
        self.odomR=0
        self.odomL=0
        self.theta=0
        self.sub_pose=rospy.Subscriber("/nunchuk/cmd_vel",Twist,self.cb_cmdvel)
        self.pub_imu=rospy.Publisher("/ZumoCarto/imu",Imu,queue_size=10)
        self.pub_odom=rospy.Publisher("/ZumoCarto/odom",Odometry,queue_size=10)
        try:
            self.PORT=rospy.get_param('ZUMO_PORT') 
        except:
            rospy.set_param('ZUMO_PORT',"/dev/ttyACM0")
            self.PORT=rospy.get_param('ZUMO_PORT')
        try:
            self.BAUDRATE=rospy.get_param('ZUMO_BAUDRATE') 
        except:
            rospy.set_param('ZUMO_BAUDRATE',"9600")
            self.BAUDRATE=rospy.get_param('ZUMO_BAUDRATE')
        self.TIMEOUT=0.1
        self.lock=Lock()
        self.centrale = list()
        self.vitesse =[]
        self.angle=[]
        self.o=Odometry()
        self.o.pose.pose.position.x = 0.0
        self.o.pose.pose.position.y = 0.0
        self.o.pose.pose.position.z = 0.0
        self.o.pose.pose.orientation.z = 0.0        
        self.o.header.stamp = rospy.Time.now()
        self.o.header.frame_id="odom"
        self.o.child_frame_id="base"
        self.p=Imu()
        self.p.header.stamp = rospy.Time.now()
        self.p.header.frame_id="imu"
        
        
        try :
            self.ser = serial.Serial( self.PORT, self.BAUDRATE,timeout=self.TIMEOUT)
            sleep(1)
            rospy.loginfo("connexion serie etablie sur le port "+str(self.PORT))

        except:
            rospy.loginfo("Echec connexion serie")
            
    def __delete__(self):
        self.ser.close()
        print "Connexion fermee"
        
    def recup_trame(self):
        with self.lock: 
           #si je rentre dedans je prends le lock et personne ne peut le prendre permet de gerer 
           #les conflits de com sur le port serie, un seul dessus a la fois
           try :
               self.ser.flush()
               sleep(0.001)
               line = self.ser.readline() # reception trame accelero/magneto/gyro
               if len(line)>0:
                   if line.startswith('!AN'):
                       line = line.replace("!AN:", "")
                       line = line.replace("\r\n", "")
                       self.centrale=line.split(',')
                       rospy.loginfo( "Trame recue : "+str(self.centrale))
                       self.pubimu()
                       self.pubodom()
           except :
               rospy.loginfo("recup trame en rade !")
              
    def envoie_consigne(self,cons_vitesse,cons_angle):
       with self.lock:
            #construction et envoie trame consigne
            consigne="~X;"+str(int (cons_vitesse*100))+";"+str(int (cons_angle*100))+";#"
            self.ser.flush()
            sleep(0.001)
            
            try :
                self.ser.write(consigne)
                #rospy.loginfo("Consigne envoyee : "+str(consigne))
            except :
                rospy.loginfo( "envoie trame en rade !")
        
    def cb_cmdvel(self,msg):
       self.envoie_consigne(msg.linear.x,msg.angular.z)
       #print "callback : ",msg
       

    def pubimu(self):
        self.p.linear_acceleration.x=4*9.81*(float(self.centrale[1])/2**16)/100 #/100 pour la vizu Rviz
        self.p.linear_acceleration.y=4*9.81*(float(self.centrale[2])/2**16)/100
        self.p.linear_acceleration.z=4*9.81*(float(self.centrale[3])/2**16)/100
        self.p.orientation.x= float(self.centrale[4])
        self.p.orientation.y=float(self.centrale[5])
        self.p.orientation.z=float(self.centrale[6])
        self.p.header.stamp = rospy.Time.now()
        self.pub_imu.publish(self.p)
    
    def pubodom(self):
        if self.centrale[10]!=self.odomR or self.centrale[9]!=self.odomL:
            deltat=(float(self.centrale[0])-float(self.temps))/1000 # en seconde
            VR=(float(self.centrale[10])-self.odomR)/self.COUNT *3.14*self.DIAMETRE/deltat #en metre
            VL=(float(self.centrale[9])-self.odomL)/self.COUNT *3.14*self.DIAMETRE/deltat #en metre
            self.odomL=float(self.centrale[9]) 
            self.odomR=float(self.centrale[10])
            self.temps=self.centrale[0]
        else :
            VR=0
            VL=0
        
        self.o.pose.pose.position.x += deltat*(VR+VL)/2*cos(-self.theta)
        self.o.pose.pose.position.y += deltat*(VR+VL)/2*sin(-self.theta)
        self.theta += deltat*(VL-VR)/self.ENTREAXE    
        
        quat = tf.transformations.quaternion_from_euler(0,0,-self.theta)
        ### Insert math into Odom msg so it can be published
        self.o.pose.pose.orientation.x = quat[0]
        self.o.pose.pose.orientation.y = quat[1]
        self.o.pose.pose.orientation.z = quat[2]
        self.o.pose.pose.orientation.w = quat[3]
        self.o.twist.twist.linear.x =(VR+VL)/2*cos(-self.theta)
        self.o.twist.twist.linear.y =(VR+VL)/2*sin(-self.theta)
        self.o.twist.twist.angular.z = (VL-VR)/self.ENTREAXE    
        self.o.header.stamp = rospy.Time.now()
        self.pub_odom.publish(self.o)
        #print self.o.pose.pose.position.x*100,self.o.pose.pose.position.y*100,self.o.pose.pose.orientation.z*360/6.28

if __name__=="__main__":


    print "Starting"
    rospy.init_node("zumo")
    myZumo=Zumo()

    while not rospy.is_shutdown():
              myZumo.recup_trame()
              sleep(0.001)

    rospy.loginfo("Node terminated")
    rospy.delete_param("ZUMO_BAUDRATE")
    rospy.delete_param("ZUMO_PORT")
    myZumo.ser.close()
    rospy.loginfo("Connexion fermee")