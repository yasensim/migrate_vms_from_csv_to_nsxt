# migrate_vms_from_csv_to_nsxt
Script that migrate VMs provided via CSV file to NSX-T Logical Switches

It migrates to NSX-T Logical Switches only, do not use for migrating to VSS ot VDS Portgroups!

You need python and pip installed on your system.
```
pip install pyvmomi
pip install pyvim
```

Clone the repo:
```
git clone https://github.com/yasensim/migrate_vms_from_csv_to_nsxt.git
```

Edit the vms.csv file with the Virtual Machines and Logical Switches in your setup.
In my example web, app, and db are the VMs and web-tier, app-tier,db,tier are the Logical Switches I want to migrate the VMs to.

```
web,web-tier
app,app-tier
db,db-tier
```

Run the script providing the full path to the CSV file:
```
python migrate.py -s 10.29.15.69 -u administrator@yasen.local -f /Users/ysimeonov/migrate_vms_from_csv_to_nsxt/vms.csv 
Enter password for host 10.29.15.69 and user administrator@yasen.local: ********
Successfully changed to network web-tier for VM web
Successfully changed to network app-tier for VM app
Successfully changed to network db-tier for VM db
```
