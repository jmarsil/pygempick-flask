# pyGemPick: Flask Web App For Automatic Immunogold Particls Detection

This is the pyGemPick web application built on top of Flask python framework. 
Here users can download the whole flask web-application or visit the live beta 
version of the website and process TEM immunogold electron microscopy images quickly,
accurately, and free of charge! Have fun detecting those gold particles!!

## Setup Redis Server on Mac (osx)

1. **Install [Homebrew](https://brew.sh/)**

2. **Install [Redis](https://medium.com/@petehouston/install-and-config-redis-on-mac-os-x-via-homebrew-eb8df9a4f298) Using brew install...** 


```bash
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

```
brew install redis
```

####Option A: Launch Redis on Computer Startup

```bash
ln -sfv /usr/local/opt/redis/*.plist ~/Library/LaunchAgents
```
#### Option B: Launch from Redis-Server Config
```bash
redis-server /usr/local/etc/redis.conf
```

##### Test if Redis server is running.

```bash
redis-cli ping
```

**Response == 'PONG'**. (Now Web-app Background Tasks can run!)

### Running Virtual Server for Background Tasks 

1. Open a separate terminal in the pypick environment. (run **_source activate pypick_**)
2. Then run...

```bash
rq worker pypick-tasks
```


## Setting up Anaconda Environment 

1. **Install Anaconda using [this tutorial](https://www.digitalocean.com/community/tutorials/how-to-install-the-anaconda-python-distribution-on-ubuntu-18-04)** 
2. **[Recreate the environment](https://datascience.stackexchange.com/questions/24093/how-to-clone-python-working-environment-on-another-machine) to run pygempick on Mac/Linux in terminal...**
3. To use new environment run **_source activate pypick_** command in mac/linux terminal.

##### Recreating condal env from .yml file
```bash
conda env create -n pypick -f pypick_env.yml
```

##### Using New Environment

```bash
source activate pypick
```

## Setting Up & Updating Database

1. Setup database using **_flask db init_** command in terminal.
2. Use **_flask db migrate_** command in terminal to update database tables.
3. To push the migration to the live app run **_flask db upgrade_**.

**Note: Run 2 & 3 every time models.py is modified** If this is not done and you accidentally delete a previous migration 
**WITHOUT** downgrading, you will have to also delete the logs with it in order to migrate successfully again.

#### How do I fix database errors?

Database errors occur as a result of an error when writing or establishing a db connection. This is frequently caused by
the most recent database change. To change downgrade database to previous saved version.

#####In Terminal Run...

```bash
flask db downgrade
```

Note: Before you run another migration, **_Old Migration MUST be deleted first._** You can do this easily in terminal
by running... (The migrations.py file can be found in the migrations folder in the project's base_dir)
 
 ```bash
rm -r enter_migration_name_here.py
 ```
 
## Validation

To test the accuracy of our web-software, we have manually counted immunogold particles across TEM images of suspended 
AL aggregates. Here's a more detailed description of [amyloid light-chain (AL) amyloidosis](http://amyloidosis.org/facts/al/).

| [AL] M | Total TEM Images Processed | Manual Counts | Particles Detected | FP | FN | Accuracy |
|--------------------|--------------------------------|---------------|--------------------|----|----|----------|
| 3.7x10-6           | 100                            | TBD           | 4894               |    |    | TBD      |
| 3.7x10-8           | 102                            | TBD           | TBD                |    |    | TBD      |
| 3.7x10-10          | 100                            | TBD           | TBD                |    |    | TBD      |
| 3.7x10-12          | 100                            | TBD           | TBD                |    |    | TBD      |


* Original dimensions of the processed .tif images were (x,y ) = (2444,3744). **This was reduced to (664, 1018) during 
picking**
* The web app was made to be a semi-automatic open-source dot counting platform. To validate the quality of picking 
& processing, external unrelated dataset of graphs were used. 
