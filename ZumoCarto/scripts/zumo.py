#!/usr/bin/env python
# -*- coding: utf-8 -*-


import serial
from math import sqrt
import rospy
from time import sleep
from threading import Lock
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu


class Zumo:
    def __init__(self):
        self.sub_pose=rospy.Subscriber("/nunchuk/cmd_vel",Twist,self.cb_cmdvel)
        self.pub_imu=rospy.Publisher("/zumo/imu",Imu,queue_size=10)
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
        self.p=Imu()
        self.p.header.stamp = rospy.Time.now()
        self.p.header.frame_id="map"
        
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
        self.p.linear_acceleration.x= (4*9.81*float(self.centrale[1])/2**16)
        self.p.linear_acceleration.y=(4*9.81*float(self.centrale[2])/2**16)
        self.p.linear_acceleration.z=(4*9.81*float(self.centrale[3])/2**16)
        self.p.orientation.x= float(self.centrale[4])
        self.p.orientation.y=float(self.centrale[5])
        self.p.orientation.z=float(self.centrale[6])
        self.pub_imu.publish(self.p)
   
   
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