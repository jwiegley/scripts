{ config, pkgs, ... }:

{
  imports = [ ./hardware-configuration.nix ];

  nixpkgs.config.allowUnfree = true;

  time.timeZone = "America/Los_Angeles";

  boot = {
    devShmSize = "5%";
    devSize    = "5%";
    runSize    = "5%";

    cleanTmpDir = true;

    loader.grub = {
      enable  = true;
      version = 2;
      device  = "/dev/disk/by-id/ata-INTEL_SSDSA2CW160G3_CVPR122104FC160DGN";
    };

    supportedFilesystems = [ "zfs" ];

    postBootCommands = ''
      ${pkgs.linuxPackages.zfs}/bin/zpool import \
          -f -d /dev/disk/by-id 14074780193388422953
      ${pkgs.linuxPackages.zfs}/bin/zfs mount -a

      ${pkgs.ethtool}/bin/ethtool -G enp4s0 rx 4096 tx 4096
      ${pkgs.ethtool}/bin/ethtool -G enp5s0 rx 4096 tx 4096

      ${pkgs.squids.latest}/bin/squid -f /etc/squid.conf

      ${pkgs.patchelf}/bin/patchelf \
          --set-interpreter ${pkgs.glibc}/lib/ld-linux-x86-64.so.2 \
          /usr/local/crashplan/jre/bin/java
      ${pkgs.bash}/bin/bash /usr/local/crashplan/bin/CrashPlanEngine start
    '';
  };

  environment = {
    etc = {
      "squid.conf".text = ''
acl bypass_parent dstdomain .haskell.org
acl bypass_parent dstdomain .netflix.com
always_direct allow bypass_parent

acl localnet src 10.0.0.0/8	# RFC1918 possible internal network
acl localnet src 192.168.0.0/16	# RFC1918 possible internal network

acl SSL_ports port 443
acl Safe_ports port 80		# http
acl Safe_ports port 21		# ftp
acl Safe_ports port 443		# https
acl Safe_ports port 1025-65535	# unregistered ports
acl CONNECT method CONNECT

cache_peer 127.0.0.1 parent 8118 7 no-query
never_direct allow all

cache_effective_user johnw
access_log /dev/null
cache_log /var/squid/cache.log
pid_filename /var/squid/squid.pid
cache_store_log none

http_access allow localhost manager
http_access deny manager
http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports
http_access allow localnet
http_access allow localhost
http_access deny all

http_port 3128

cache_dir ufs /var/squid 10000 16 256
coredump_dir /var/squid

refresh_pattern ^ftp: 1440 20% 10080
refresh_pattern ^gopher: 1440 0% 1440
refresh_pattern -i \.(gif|png|jpg|jpeg|ico)$ 10080 90% 43200 override-expire ignore-no-cache ignore-no-store ignore-private
refresh_pattern -i \.(iso|avi|wav|mp3|mp4|mpeg|swf|flv|x-flv)$ 43200 90% 432000 override-expire ignore-no-cache ignore-no-store ignore-private
refresh_pattern -i \.(deb|rpm|exe|zip|tar|tgz|ram|rar|bin|ppt|doc|tiff)$ 10080 90% 43200 override-expire ignore-no-cache ignore-no-store ignore-private
refresh_pattern -i \.index.(html|htm)$ 0 40% 10080
refresh_pattern -i \.(html|htm|css|js)$ 1440 40% 40320
refresh_pattern . 0 40% 40320
'';
    };
  };

  networking = {
    hostName = "titan";
    hostId = "00000001";

    bonds = {
      bond0 = {
        interfaces = [ "enp4s0" "enp5s0" ];
        miimon = 100;
        mode = "802.3ad";
      };
    };
    interfaces.bond0 = {
      ipAddress = "192.168.9.133";
      prefixLength = 24;
    };
    defaultGateway = "192.168.9.1";
    nameservers = [ "192.168.9.1" ];

    firewall = {
      enable = false;
      allowPing = true;
      allowedTCPPorts = [ 445 139 3128 4242 4243 6697 ];
      allowedUDPPorts = [ 137 138 ];
      allowedUDPPortRanges = [ { from = 60000; to = 61000; } ];
    };
  };

  environment.noXlibs = true;
  environment.systemPackages = with pkgs; [
    vim rsync screen mosh git gitAndTools.gitAnnex mailutils samba
    iotop ethtool busybox smartmontools parted squids.latest jre
    socat2pre htop patchelf cacert python iperf aria2 ipmitool minidlna
    (callPackage /root/facebook.nix {})
  ];

  services = {
    zfs.autoSnapshot.enable = true;

    openssh.enable = true;
    openssh.permitRootLogin = "yes";

    rsyncd.enable = true;
    rsyncd.modules = {
      public = { path = "/tank/Public"; comment = "Public"; };
    };

    acpid.enable = true;
    apcupsd.enable = true;

    znc.enable = true;
    znc.user = "johnw";
    znc.dataDir = "/home/johnw/.znc";
    znc.zncConf = builtins.readFile /home/johnw/.znc/configs/znc.conf;

    bitlbee.enable = true;
    bitlbee.interface = "127.0.0.1";
    bitlbee.portNumber = 6698;

    minidlna = {
      enable = true;
      mediaDirs = [ "V,/tank/iTunes/Home Videos"
                    "V,/tank/Nasim/Movies"
                    "V,/tank/Rentals"
                    "V,/tank/Movies" ];
    };

    postfix = {
      enable = true;
      domain = "newartisans.com";
      hostname = "titan.newartisans.com";
      extraConfig = ''
inet_protocols = ipv4
relayhost = smtp.gmail.com:587

# auth
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = static:jwiegley@gmail.com:fhyezkwpddaayqaz
smtp_sasl_security_options = noanonymous
smtp_sasl_mechanism_filter = plain

# tls
smtp_use_tls = yes
smtp_tls_CAfile = /etc/ssl/certs/ca-bundle.crt
smtp_tls_security_level = secure
smtp_tls_session_cache_database = /tmp/smtp_scache
smtp_tls_session_cache_timeout = 3600s
smtp_tls_loglevel = 1
tls_random_source = dev:/dev/urandom
      '';
      networks = [ "192.168.9.1/16" "10.8.0.1/24" ];
      networksStyle = "subnet";
      rootAlias = "jwiegley@gmail.com";
      setSendmail = true;
    };

    privoxy.enable = true;
    privoxy.extraConfig = ''
      actionsfile match-all.action
      actionsfile default.action
    '';

    samba.enable = true;
    samba.extraConfig = ''
      workgroup = WORKGROUP
      server string = titan
      netbios name = titan
      max protocol = smb2

      strict allocate = yes
      socket options = TCP_NODELAY SO_RCVBUF=131072 SO_SNDBUF=131072

      [tank_Archives]
        path = /tank/Archives
        read list = johnw, nasimw
        write list = johnw

      [tank_Backups_Images]
        path = /tank/Backups/Images
        read list = johnw, nasimw
        write list = johnw

      [tank_Rentals]
        path = /tank/Rentals
        read list = johnw, nasimw
        write list = johnw

      [tank_Nasim]
        path = /tank/Nasim
        read list = johnw, nasimw
        write list = johnw, nasimw
    '';

    smartd.enable = true;
    smartd.deviceOpts = "-a -o on -S on -n standby,q -s (S/../.././02|L/../../7/04) -W 4,35,40 -m jwiegley@gmail.com";
  };

  security = {
    grsecurity.config.priority = "performance";

    sudo.enable = true;
    sudo.wheelNeedsPassword = false;
  };

  users.extraUsers = {
    johnw = {
      group = "users";
      uid = 501;
      createHome = false;
      home = "/home/johnw";
      useDefaultShell = true;
    };

    nasimw = {
      group = "users";
      uid = 502;
      createHome = false;
      home = "/tank/Backups/Nasim";
      useDefaultShell = true;
    };
  };

  virtualisation = {
    docker.enable = true;
  };

  programs.bash.promptInit = "PS1=\"# \"; PROMPT_COMMAND=";
}
