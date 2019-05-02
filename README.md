# SONA-CNI
SONA Container Network Interface (CNI) implements standard CNI APIs, aims to support Kubernetes network using ONOS. The [sona-cni repository] (https://github.com/sonaproject/sona-cni) contains code which makes the interaction between ONOS and Kubernetes possible. For more information visit [ONOS] (http://onosproject.org/) and [Kubernetes] (https://kubernetes.io/) projects.

# Installation
OS requirements: CentOS 7.5

1. Install python-pip and git.
```
$ sudo yum install epel-release -y
$ sudo yum install python-pip git -y
```

2. Clone sona-cni repo.
```
$ git clone https://github.com/sonaproject/sona-cni.git
```

3. Install all python dependencies.
```
$ cd sona-cni
$ sudo pip install -r requirements.txt
```

4. Configure sona-cni if needed. The configuration file is located under following path `etc/sona/sona-cni.conf`.

5. Install sona-cni.
```
$ sudo python setup.py install
```

# Important Pointers
* For latest updates, visit [project page] (https://github.com/sonaproject/sona-cni).
* Report bugs or new requirement(s) on the [bug page] (https://github.com/sonaproject/sona-cni/issues).
* Any contribution is appreciated.
* Start contributing and enjoy ;)
