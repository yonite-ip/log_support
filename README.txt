1 . ## switch to this dir
        cd /home/admin

2.  ## clone this repository
        git clone https://github.com/yonite-ip/log_support.git

3.  ## enter the folder that was cloned
        cd /log_support

4.  ## install python3 and python3 venv 
        apt install python3 python3-venv 

5.  ## create virtual Environment
        python3 -m venv env

6.  ## activate the virtual Environment
        source env/bin/activate
    
    ## should be (env) root@rnd1-dev:/home/admin/log_support#
        pip install -r requirements.txt

7. ## go out from the virtual Environment
        deactivate

8. ## copy the log_support.service file  
        cp /home/admin/log_support/log_support.service /etc/systemd/system/
   ## check if it exists 
        cat /etc/systemd/system/log_support.service

9. ## activate the server
        systemctl daemon-reload
        systemctl enable log_support
        systemctl start log_support

   ## You should see the service as active (running)
        systemctl status log_support

10. ## give admin permission to read freeswitch files
    sudo usermod -a -G freeswitch admin