# Amazon EC2 cloud computing

TOPAS refinements can be run on the Amazon Web Services (AWS) cloud platform utilizing the Amazon Elastic Compute Cloud (Amazon EC2) computing platform: “TC-Cloud”. TC-Cloud is an optional, EXPERIMENTAL FEATURE within TOPAS and its use has following provisions:

TC-Cloud is not part of the official TOPAS-Academic V8 feature set. TC-Cloud is provided to get early feedback for possible future products. Its use is for internal testing purposes.

TC-Cloud is provided AS IS without warranty of any kind and without obligation to provide any support such as installation support, usage support, error corrections, and/or any enhancements to the feature.

Using non-free AWS resources does incur AWS fees. The user is responsible for all AWS costs. Coelho software is not liable for any loss arising out of the use of TC-Cloud; any damages arising out of the use of TC-Cloud is borne by the User.

The TC-Cloud feature can be cancelled at any time in future updates or upgrades, for any reason, and without notice.

TC-Cloud can be run on 100s of virtual computers on the Amazon Web Services (AWS) cloud platform. The process is driven from the GUI version of TOPAS/TOPAS-Academic, where launching an INP file on the cloud is a few mouse-clicks away. The Cloud gives access to large computing resources where 1000s of virtual machines (VMs) can be utilized in a relatively inexpensive manner. Large simulated-annealing problems taking weeks on a laptop can be done in minutes. The process typically involves working interactively with TOPAS in Launch mode and performing initial preliminary refinements. Once the User is satisfied, the Cloud version of the kernel, which we will call TC-Cloud, can be launched. Cloud operation is often performed in an interactive manner due to the speed of analysis; many Cloud runs need only last for 10 to 20 minutes depending on the number of VMs used.

The User does not install TC-Cloud; instead, TC-Cloud is pre-installed on a Virtual Machine image called an Amazon Machine Image (AMI). The AMI for TC-Cloud is called TC-AMI. TC-AMI can be used to create many virtual machines each corresponding to a virtual Linux computer; we will call these TC-VMs. Each TC-VM can run multiple instances of TC-Cloud. To summarize:

TA.EXE is the GUI version of TOPAS running on a local computer.

TC-Cloud is the cloud version of TOPAS running on a VM.

TC-AMI is an image of a VM with TC-Cloud installed.

TC-VM is a VM created from TC-AMI.

Many TC-VMs (500 for example) can be created/deleted at once.

The user is given a choice of VM type when launching TC-AMI to create TC-VMs. A large TC-VM can run more than one instance of TC-Cloud.


## Operation

TC-Cloud operates in a similar but not identical manner to TC.EXE. Importantly INP files are pre-processed before launching on the Cloud; this ensures the use of local files such as TOPAS.INC and other #include files. Since the local TOPAS.INC is used then local emission profiles are used. Data files referenced in the INP file must reside in the same local directory as the INP file. This is normal practise and INP files should therefore not contain file paths. For example,

this is valid on the Cloud:			xdd data.xy

this is not valid on the Cloud:		xdd data\data.xy

File names on Linux are case sensitive. It is therefore important to use the correct case when referring to file names within INP files. The following keywords can be included in INP files but have been disabled:


| append_bond_lengths atom_out A_matrix A_matrix_normalized bootstrap_errors C_matrix C_matrix_normalized do_errors | do_errors_include_penalties do_errors_include_restraints index num_runs out out_file out_prm_vals_dependents_filter out_prm_vals_filter out_prm_vals_on_convergence out_prm_vals_on_end | out_prm_vals_per_iteration phase_out phase_out_X process_times system_after_save_OUT  system_before_save_OUT verbose view_structure xdd_out |
| --- | --- | --- |

Many of these refer to data output and as such are better left to the local computer.


## Pre-requisites

Signing up with Amazon AWS is required, see https://aws.amazon.com/. Also, necessary is TOPAS/TOPAS-Academic and a local computer to run TOPAS. TC-AMI comes with TOPAS/Academic Version 7; access to TC-AMI can be obtained from Alan Coelho. TC-VMs are monitored and terminated depending on User defined conditions. For example, VMs can be terminated when the best goodness of fit parameter (GOF) from all TC-VMs drop below a User defined value. This reduces running times for the TC-VMs and consequently running costs. The following points are important:

Signing up with AWS does not incur a fee.

Using non-free AWS resources does incur AWS fees.

The User is responsible for all AWS costs.

AWS fees can be reduced by reducing the use of AWS services.

VMs created as spot instances are often 60 to 70% cheaper.

Services can be reduced by:

Turning off unused VMs.

Deleting unused VMs.


## Pricing of AWS cloud resources

The following approximate pricing information is dependent on AWS and could change. Running TOPAS on AWS requires the use of VMs. Each VM in turn uses an EBS volume (a storage device). Use of both the VM and the EBS incur AWS fees, see:

For VMs: https://aws.amazon.com/ec2/pricing/on-demand/

For EBS volumes: https://aws.amazon.com/ebs/pricing/

Limited usage of a single core VM on Amazon AWS are free of charge for a period of one year. Large VMs (ones with many cores) are not free with charges dependent on time usage. Pricing is on a per second basis for Linux VMs; the twin core VM c5.large is recommended for routine TC-Cloud usage; for the same core count, it is equivalent to an average high end laptop in computational speed and is priced at approximately ~0.034 cents USD (for spot instances) per hour. One hundred of these running for one hour will cost approximately $3.40 USD. Large saving, often up to 70%, can be realized by requesting spot-instances, see https://aws.amazon.com/ec2/spot/pricing/. The author has had no trouble getting regular access to 500 spot instances.

Each TV-VM is a Linux VM; it comes with an 8 Gbyte EBS volume which stores TC-Cloud and the operating system. EBS volumes are relatively inexpensive at 0.125 USD per Gbyte per month, or $1 USD per month for each TC-VM. For one hundred VMs this small charge becomes $100 USD per month. It is therefore recommended that VMs are deleted after use to reduce costs. Creating and starting VMs takes one to two minutes.

Cloud storage is required in addition to VMs and associated EBS volumes. This storage is used to transfer data from the local computer to the VMs and visa-versa. AWS S3 cloud storage is used; it is inexpensive and runs at approximately $0.02 per Gbyte per month, see https://aws.amazon.com/s3/pricing/. File manipulation of S3 storage is provided online via the AWS Dashboard. Running TC-Cloud typically requires a fraction of a Gbyte in S3 storage and hence common storage costs are negligible.


## AWS dashboard and operating TC-Cloud

AWS includes a comprehensive browser dashboard called EC2 Dashboard https://ap-southeast-2.console.aws.amazon.com/ec2/. In the case of running TC-Cloud, the dashboard is primarily used to create TC-VMs from TC-AMI as well as deleting files created on the S3 cloud storage. The rest of TC-Cloud operations are performed from TA.EXE. The important parts of EC2 Dashboard are circled in the following:

Note: AWS web screens may change due to improvements etc…; the general operation however should remain the same. Clicking on the Account (circled on the top) brings up account options which includes real time billing information (AWS Cloud costs). Also on the top, is the AWS region being operated-on. AWS operates on a regional basis; regions chosen should be in close geographical proximity to the local computer. This reduces response times and data transfer costs. TC-VMs are created by clicking on AMIs. Once created, details of TC-VMs for the selected region can be viewed by clicking on Instances. AWS limits the number of VMs available to 20 on most VM types; request for increasing this number can be made from the circled ‘Limits’ item. The author had no trouble getting regular access to 500 spot instance VMs.


## Installing AWS CLI on the local computer

For communicating with the TC-VMs; the local computer requires the installation of the AWS Command Line Interface (CLI). The CLI can be trivially installed and downloaded from:

https://docs.aws.amazon.com/cli/latest/userguide/install-windows.html.


## Operating TC-Cloud from TOPAS (GUI)

After the preliminary setting up and testing of an INP file with TA.EXE on the local computer, the INP file can be fed to AWS for parallel operation on many VMs. Summing up the process we have:

Set up INP file and ensure it runs as expected on TA.EXE on the local computer.

Create a small number of VMs (3 for example) and ensure that the INP file runs as expected on the VMs.

Create many more VMs (User determined) and run the INP file on the VMs.

Stage-1 is normal TOPAS operation. Stage-2 involves creating a job (*.CLD files) from the 'Setup Cloud' tab in the GUI. Before creating a job, it's best to create a template that can be used for all jobs in the AWS region. Enter your 'Key pair file', the AWS Region being used and your S3 bucket name details in the Setup Cloud tab; it should look something like:

Save the details using ‘Save-As CLD setup file’ to a file. Load this file when creating other CLD files. To run a job then enter the rest of the setup details; an example is:

The highlighted lines require input of the INP file to be run on the Cloud as well as the necessary data files. In the above the INP file is placed in the S3 job directory called 2wfi-1 and the data file is placed in the S3 directory called 2wfi. S3 will therefore contain the following two directories:

s3://aacbucket1/swfi-1

s3://aacbucket1/swfi

The INP file as well as other communication files are copied to the job directory, 2wfi-1 in this case. The name of the INP file on S3 is changed to in.inp; in.inp is used in the retrieval of output from the VMs; it is unchanged during Cloud operation, and it can be also viewed as a backup for the job. Each run on the Cloud requires a unique job name; an exception is thrown otherwise. Many jobs, however, can use the same S3 data directory. In cases where many jobs are run sequentially, each using the same data files, then the ‘Copy data to S3’ option can be set to No after the first job; this speeds-up processing as copying large data files over the internet can be slow. CLD files contain information necessary for launching the INP file on the cloud. Once the information is entered, it becomes possible to view the created VMs in the ‘Virtual Machines’ tab, or:

Data can be displayed in sorted order by double clicking on the column headings. To launch the INP file on a VM, select the VM and click 'Run TC on selected VMs'. To select all VMs, click on the empty circled rectangle shown. Only VMs with an ok Status can be launched. If a selected VM is 'starting' or 'pending' then Status will not be ok. The number of TCs running on each VM (typically one) is shown in the # TCs column. This data, as well as other VM details, maybe out-of-date; to show the latest, click on the Refresh option. The iters column shows the total number of refinement iterations executed on the respective VM; this number supplies a means of determining if a VM is running in an expected manner. For example, if iters has stopped increasing in an expected manner and #TCs is not zero then the running TCs have stopped operating in an expected manner.

Due to the speed of analysis, Cloud operation is often performed interactively. Running many jobs to investigate a problem, each taking 10 to 20 minutes and comprising 500 VMs, is common. Each job creates a directory on S3 which can be deleted after use using the AWS S3 dashboard; it looks like:


## Terminating/Stopping TC-VMs and tc-mon.a

Terminating or stopping TC-VMs reduces AWS fees. TC-VMs can be automatically stopped or terminated depending on ’End conditions’, or:

These conditions are uploaded to the VMs when a job is launched. On launching a job, a small monitoring program, called tc-mon.a, is started on each VM. This monitoring program reads the End conditions and monitors the running TCs. VMs are in turn terminated/stopped depending on the End conditions. From the local machine, the end conditions can also be uploaded after a job has started using the 'Upload to selected VMs' option. This option has no effect on VMs with a Status that is not ok. The 'Refresh' option displays values as found on common storage for the job indicated in 'Setup cloud' tab.

TCs running on VMs are terminated when the number or iters, as defined in the INP file, has been reached, or, when the CPU time allocated 'Max time (s)' has been reached or when the overall best GOF falls below 'GOF Target'. When there are no TCs running on a VM then the VM is stopped if 'Off on End'=1; subsequently if 'Del on end'=1 then the VM itself is terminated (deleted). Parameters for a typical job left unattended would be:

Max time (s) = 10 60 60 = 10 hrs of running

GOF Target = 10,   Off_on_End = 1,   Del_on_end = 1

For interactive use, the user can manually terminate TCs and VMs; the termination parameters could therefore look something like:

Max time (s) = 0

GOF_Target = 10, Off_on_End = 0, Del_on_end = 0

A 'Max time (s)' of zero (the default) disables the ending of TCs on a time basis. 'Max time (s)' on VMs can be entered as an equation by starting the equation with an equal sign. For example, '= 24 60 60' could be used to enter 24hrs.


## Powering off TC-VMs after 100 minutes of inactivity

In addition to the terminating/stopping criteria of the previous section, VMs are automatically powered off (stopped but not terminated) after 100 minutes of TC-Cloud inactivity, including inactivity on VM start-up. The net effect is that VMs are stopped after 100 minutes of TC-cloud not being run. Situations where 100 minutes of inactivity is possible include internet-down situations as well as Users forgetting to power-off or terminate VMs. For example, the fee incurred for forgetting to turn off 100 spot instance VMs would be ~3.40 USD.


## Retrieving the INP or FC file that gave the best GOF

Output from a job, corresponding to the best INP for Rietveld refinement, or the best structure factors for charge-flipping, is stored on the S3 job directory. This storage to S3 from a job is independent of the local computer. The ‘Get best overall’ downloads the output from S3 to the local directory where INP file originated. The name given to the output is Job-Name.INP for Rietveld refinement or Job-Name.FC for charge-flipping. For example, for a job named ‘PbSO4-1’ and an input file with a path of c:\data\PbSO4.inp we get:

‘INP File for cloud’ = c:\data\PbSO4.inp

‘Get best overall’ places output in c:\data\PbSO4-1.inp

Once retrieved, the best INP file can be run on the local computer; in other words, the best fit from the Cloud can be visually inspected with a few mouse clicks. If the VMs are available and not stopped or terminated, then output from the individual VMs can be retrieved using the ‘Get best for selected’ option; output is placed in the local computer in a manner identical to that described for ‘Get best overall’. Typical interactive operation therefore comprise viewing and partially running intermediate Cloud results and making decisions based on those results.


## Monitoring, TC-Cloud is independent of the local computer

The running of VMs can be monitored by the local computer using the ‘Monitoring is On/Off’ option. When On, the best overall GOF is displayed in the text output of the ‘Fit Dialog’ window at time intervals as defined in ‘Monitoring time interval’ option of ‘Setup cloud’ tab. Whilst jobs are running, the local computer can be used to run refinements independent of Cloud jobs. Cloud jobs can be started on a laptop, left running overnight and results viewed the next day.


## Random number generator automatically seeded

The random number generator for both TC-Cloud (and TC.EXE on the local computer) is seeded such that the sequence of random numbers generated for any run is unique. Identical sequences can be generated by using the seed keyword with an integer (corresponding to a seed number) placed after it.


## CLOUD__  #define and Get(cloud_run_number)

The pre-processor directive of ‘#define CLOUD__’ is automatically included at the start of INP files running on VMs. This allows blocks of INP script to be conditionally included/excluded from Cloud runs making it easy to run the same INP file in both the Cloud and on the local computer. For example, the following is useful in the case of charge-flipping:


| charge_flipping  #ifdef CLOUD__ randomize_initial_phases_by = Rand(-180, 180); #else set_initial_phases_to job-name.fc #endif |
| --- |

Here the state of the best FC file found on the VMs can be determined by first executing the ‘Get best overall’ option and then locally running the INP file. Also, available is Get(cloud_run_number) which returns the run number assigned to the corresponding VM with counting starting at 0. Get(cloud_run_number) returns -1 when running on the local computer. Example usage in terms of stacking faults could be:


| macro & pa { Get(cloud_run_number+1)/102 }  generate_stack_sequences { number_of_sequences 200 number_of_stacks_per_sequence 200 Transition(1, lpc) to 1 = pa;      a_add = 2/3;   b_add = 1/3; to 2 = 1-pa;    a_add = 0;     b_add = 0; Transition(2, lpc) to 1 = 1-pa;    a_add = 0;     b_add = 0; to 2 = pa;      a_add = -2/3;  b_add = -1/3; } |
| --- |


## ‘Setup Cloud’ details

Cloud setup file

File name containing cloud details for a job.

Key pair file

File name containing encrypted login information, see:

https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html

This file needs to be read/write protected so that only one user can access; use Windows Explorer and Right-Click on the file to change its properties.

Region

Geographical region where VMs reside.

S3 Bucket

The name of the bucket for transferring data to and from the TC-VMs. Buckets are created and manipulated at https://s3.console.aws.amazon.com/s3/. By default, S3 buckets are private to the User. Once a bucket is created, directories within the bucket corresponding to the job name are automatically created on launching the TC-VMs. For example, for a job named job-1 and a bucket called my-bucket then the following directory on S3 is created:

s3://my-bucket/job-1

my-bucket are used for many jobs. Information stored on common storage are not deleted by TA.EXE running on the local computer; the User is therefore responsible for cleaning up unwanted files using the AWS S3 dash-board.

Job Name

Name of job. Job names cannot contain spaces.

S3 data directory

Directory where data files are stored. More than one job can use an S3 data directory.

INP file for cloud

Input file to run on the Cloud. The INP file can make use of the predefined pre-processor directive called CLOUD__. It can also make use of Get(cloud_run_number).

Number TCs per VM

Typically set to 1. The number of TC-Cloud instances to run on each TC-VM. The number of TCs per VM should not exceed the number of Cores as seen in the Cores column of the Virtual Machines tab. For example, the VM type of c5.18xlarge has 36 Cores each with 2 threads (intel hyper threading). The number of TCs therefore should not exceed 36. Information on EC2 instance types can be found at https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-optimize-cpu.html.

Max threads per TC

Typically set to 2 for c5.large VMs. The maximum number threads each TC can use. If zero, then each VM will be allowed to use the maximum number or threads. For VMs with more than one TC running, the maximum number threads should be set to:

Max_threads_per_TC = (Virtual Cores) / Number_TCs_per_VM

Monitoring time interval (s)

The time interval used when ‘Monitoring is On’.


## ‘Virtual Machines’ tab options

Refresh

Refreshes VMs details corresponding to the region defined in the ‘Setup cloud’ tab.

Run TC on selected VMs

Launches TC-Cloud on selected VMs.

Get best overall

Gets and processes the best output from common storage for the job defined in Setup cloud and places the result in the directory where the original INP file came from. For Rietveld refinement the retrieved output is placed in a file called job-name.INP. For charge-clipping, the retrieved output (structure factors) is placed in a file called job-name.FC. Files placed in common storage persists and are therefore available even after the job’s VMs are deleted.

Get best for selected

Gets and processes the best output from a selected VM and places the result in the directory of the original INP file. The selected VM must be On. For Rietveld refinement the retrieved output is placed in a file called job-name.INP. For charge-clipping, the retrieved output (structure factors) is placed in a file called job-name.FC.

End TC on selected VMs

Stops any TC-Clouds running on selected VMs. On termination of the TCs, the VMs are turned off if their corresponding Off_on_End=1; in turn VMs are terminated if their corresponding Del_on_End=1.

Monitoring is On/Off

Starts/Stops monitoring. When monitoring is On, the best GOF as found by the TC-VMs for the job defined in ‘Setup cloud’ is displayed in the Fit Dialog.

Turn On selected VMs

Turns selected VMs On.

Turn Off selected VMs

Turns selected VMs Off.

Console for selected VMs

Log-in to the selected VMs creating terminal windows for each. Can be useful for trouble shooting.


## Creating TC-VMs – Spot Instances

TC-VMs are created from the EC2 dashboard. To create 200 VMs, for example, click on the AMIs option and then click on the TC-AMI-n AMI. n corresponds to the latest TC-AMI version. Then click on Launch to bring up ‘Choose an Instance Type’ screen. Choose an appropriate VM type; for refinements that require less than 4Gbytes of memory then choose c5.large. The amount of memory required for each TC can be determined by first running the INP file on the local machine and viewing the Windows Task Manager. Once the VM type is chosen, proceed to the next screen ‘Configure Instance Details’:

Set ‘Number of instances’ to 200 and set the ‘IAM role’ to ‘ecsInstanceRole’. Select ‘Request Spot instances’. Spot instances are often 60 to 70% cheaper; the user is informed when spot instances are unavailable; the author has had no difficulty obtaining 500 spot instances on a regular basis. Proceed to the ‘Configure Security Group’ screen and set the Source to ‘My IP’; ie.

Click on ‘Review and Launch’ to Launch the creation of the TC-VMs. Creation should take one to two minutes. Use the TA Refresh option of ‘Virtual Machines’ to see the status of VMs; VMs with a Status of ok are ready to run. Once all the VMs are created, the ‘Run TCs on selected VMs’ option from the Virtual Machines tab can be used to launch the job on the selected VMs.


## Choosing the optimum VM type

The most appropriate VM for TOPAS type problems are c5.large where memory usage is less than 4 Gbytes. However, a problem that uses 20 Gbytes of memory would need a larger VM; such problems could be a large charge flipping refinement, a large Rietveld refinement or a simulated annealing refinement with 1000s of parameters. Memory usage prior to launching on the Cloud can be determined using the local computer. The VM type chosen should therefore be one than has more memory than the maximum memory usage seen on the local computer. Only c* types (compute types) VMs should be chosen (see https://aws.amazon.com/ec2/pricing/on-demand/). For a problem that uses 20 Gbytes of memory, the c5.4xlarge is the smallest VM that will do the job. Max Number of threads should be set to zero allowing the maximum number of threads to be used which in this case is probably 16.

Note, TOPAS is threaded to a large extent, however, an excessive number of threads could slow down execution. For example, the large VM type of c5.18xlarge operating on the test_exampleS\single-crystal\pn_o2_2-adps.inp (3970 parameters) produces the following as a function of number of threads:


| # of Threads | approximate_A - 15 iterations | approximate_A - 15 iterations | Full A matrix - one iteration | Full A matrix - one iteration |
| --- | --- | --- | --- | --- |
| # of Threads | Time(s) | Gain | Time(s) | Gain |
| 2 | 42.19 | 0.32 |  |  |
| 4 | 22.28 | 0.60 | 186.98 | 0.36 |
| 8 | 8.41 | 1.59 | 61.93 | 1.09 |
| 16 | 4.11 | 3.25 | 31.65 | 2.12 |
| 32 | 2.77 | 4.82 | 17.92 | 3.75 |
| 48 | 2.89 | 4.62 | 15.18 | 4.43 |
| 64 | 2.95 | 4.53 | 13.71 | 4.91 |
| 70 | 3.06 | 4.37 | 13.73 | 4.90 |

The columns marked Gain are the times taken on a high-end laptop with 8 threads divided by the time taken on c5.18xlarge. The speedup due to number-of-threads is substantial up to about 32 threads. It is worth noting that TOPAS V7 for the approximate_A case is 1.9 times faster than V6.


## Unable to connect to TC-VMs after local computer restart

The IP address of the local computer may change when the local computer is powered off and restarted, or, when the connection to the internet changes. VMs created prior to the restart would therefore have an invalid local-computer-IP-address; communication with the VMs would therefore not be possible. This scenario is noticed when the Refresh or ‘Run TCs on selected VMs’ options of the ‘Virtual Machines’ tab is not responsive. In such a case it is necessary to instruct the VMs that the IP address has changed. This can be performed from the Instances of the EC2 Dashboard; from this screen click on the security group shown in the ‘Security Groups’ column. This brings up details of the security group. Click on Inbound and then Edit and then change the Source to My IP, or,
