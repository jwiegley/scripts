#!/opt/local/bin/ruby

require 'yaml'

BOOST = "1.49"

def my_ipaddr intf
  `ifconfig #{intf} inet`.lines.grep /inet ([0-9.]+) netmask/ and $1
end

def qping host, ipaddr=host
  `ping -c1 -W50 -q #{host}`.index('(' + ipaddr + ')')
end

def find_env
  my_ip = (my_ipaddr 'bond0' or my_ipaddr 'en0' or my_ipaddr 'en1')

  result = {
    found:  false,
    laptop: false,
    remote: nil,
    jobs:   1,
    hosts:  nil
  }

  if my_ip == '192.168.9.141'
    result[:jobs]   = 22
    result[:laptop] = false

    if qping '192.168.9.131'
      result[:found]  = true
      result[:remote] = 'hermes'
      result[:hosts]  = 'localhost/12 @hermes/4'
    elsif qping '192.168.9.123'
      result[:found]  = true
      result[:remote] = 'hermesw'
      result[:hosts]  = 'localhost/12 @hermesw/4'
    elsif system 'ssh -o ConnectTimeout=10s -p 2020 localhost true'
      result[:found]  = true
      result[:remote] = 'hermesf'
    else
      result[:jobs]   = 18
      result[:hosts]  = 'localhost/16'
    end
  else
    result[:jobs]   = 18
    result[:laptop] = true

    if qping '192.168.9.141'
      result[:found]  = true
      result[:remote] = 'vulcan'
      result[:hosts]  = 'localhost/4 @vulcan/16'
    elsif (myip != '192.168.9.131' and myip != '192.168.9.123' and
           system 'ssh -o ConnectTimeout=10s home true')
      result[:found]  = true
      result[:remote] = 'home'
      result[:hosts]  = 'localhost/4 @home/16'
    else
      result[:jobs]   = 6
      result[:hosts]  = 'localhost/4'
    end
  end

  result
end

if File.exists? '/tmp/distcc.env'
  settings = nil
  File.open('/tmp/distcc.env') { |fd| settings = YAML::load fd.read }
else
  settings = find_env
  File.open('/tmp/distcc.env', 'w') { |fd| fd.puts YAML::dump(settings) }
end

system 'launchctl limit maxproc 512'

ENV['CCACHE_PREFIX']   = 'distcc'
ENV['DISTCC_DIR']      = "#{ENV['HOME']}/.distcc"
ENV['DISTCC_SSH']      = 'ssh'
ENV['DISTCC_FALLBACK'] = '0'
#ENV['DISTCC_VERBOSE']  = '1'
ENV['DISTCC_HOSTS']    = settings[:hosts]

compiler = 'clang++'

if ARGV.include?('--gcc')
  ARGV.delete('--gcc')
  ARGV << '--gcc48'
end

debug = ARGV.include?('-g') || ARGV.include?('-g2')

arg = ARGV.grep(/--boost=([0-9.]+)/)
if not arg.empty?
  BOOST = arg[0].sub('.', '_')
  ARGV.delete_if { |item| item =~ /^--boost/ }
end

if BOOST and not ARGV.include? '-c' and not ARGV.grep '\.[gp]ch$'
  ARGV << '-lboost_date_time'
  ARGV << '-lboost_filesystem'
  ARGV << '-lboost_iostreams'
  ARGV << '-lboost_regex'
  ARGV << '-lboost_system'
end

case
when ARGV.include?('--gcc42')
  ARGV.delete('--gcc42')

  compiler = '/usr/bin/g++'

  if BOOST
    ARGV << '-isystem' << "/usr/local/include/boost-#{BOOST}"

    ARGV.map! do |elem|
      if elem =~ /-lboost_([^-]+)$/
        if debug
          elem + "-xgcc42-d-#{BOOST}"
        else
          elem + "-xgcc42-#{BOOST}"
        end
      else
        elem
      end
    end
  end

  ARGV << '-isystem' << '/opt/local/include'
  ARGV << '-isystem' << '/usr/local/include'

  unless ARGV.include? '-c' or ARGV.grep '\.gch$'
    ARGV << '-Wl,-L/opt/local/lib'
    ARGV << '-Wl,-L/usr/local/lib'
  end

when ARGV.include?('--gcc47')
  ARGV.delete('--gcc47')

  compiler = '/opt/local/bin/g++-mp-4.7'

  if BOOST
    ARGV << '-isystem' << "/usr/local/include/boost-#{BOOST}"

    ARGV.map! do |elem|
      if elem =~ /-lboost_([^-]+)$/
        elem + "-xgcc47-#{BOOST}"
      else
        elem
      end
    end
  end

  ARGV << '-isystem' << '/usr/local/include'
  ARGV << '-isystem' << '/opt/local/include'

  unless ARGV.include? '-c' or ARGV.grep '\.gch$'
    ARGV << '-Wl,-L/usr/local/lib'
    ARGV << '-Wl,-L/opt/local/lib'
  end

when ARGV.include?('--gcc48')
  ARGV.delete('--gcc')
  ARGV.delete('--gcc48')

  compiler = '/opt/local/bin/g++-mp-4.8'

  if BOOST
    ARGV << '-isystem' << "/usr/local/include/boost-#{BOOST}"

    ARGV.map! do |elem|
      if elem =~ /-lboost_([^-]+)$/
        if debug
          elem + "-xgcc48-d-#{BOOST}"
        else
          elem + "-xgcc48-#{BOOST}"
        end
      else
        elem
      end
    end
  end

  ARGV << '-isystem' << '/usr/local/include'
  ARGV << '-isystem' << '/opt/local/include'

  unless ARGV.include? '-c' or ARGV.grep '\.gch$'
    ARGV << '-Wl,-L/usr/local/lib'
    ARGV << '-Wl,-L/opt/local/lib'
  end

when (ARGV.include?('--intel') or ARGV.include?('--icc'))
  ARGV.delete('--icc')
  ARGV.delete('--intel')

  if ARGV.include?('-O3')
    ARGV.delete('-O3')
    ARGV << '-fast'
  end

  compiler = '/opt/intel/bin/icc'

  if BOOST
    ARGV << '-isystem' << "/usr/local/include/boost-#{BOOST}"

    ARGV.map! do |elem|
      if elem =~ /-lboost_([^-]+)$/
        if debug
          elem + "-il-d-#{BOOST}"
        else
          elem + "-il-#{BOOST}"
        end
      else
        elem
      end
    end
  end

  ARGV << '-isystem' << '/opt/local/include'
  ARGV << '-isystem' << '/usr/local/include'

  ARGV << '-Wl,-L/opt/local/lib'
  ARGV << '-Wl,-L/usr/local/lib'

when ARGV.include?('--clang30')
  ARGV.delete('--clang30')

  compiler = '/usr/bin/clang++'

  ARGV << '-isystem' << '/opt/local/include'
  ARGV << '-isystem' << '/usr/local/include'

  unless ARGV.include? '-c' or ARGV.grep '\.pch$'
    ARGV << '-Wl,-L/opt/local/lib'
    ARGV << '-Wl,-L/usr/local/lib'
  end

else
  ARGV.delete('--clang')
  ARGV.delete('--clang31')

  compiler = '/usr/local/stow/clang-3.1/bin/clang++'

  if ARGV.include?('-std=c++11')
    ARGV << '-Qunused-arguments'
    ARGV << '-nostdlibinc'
    ARGV << '-isystem' << '/usr/local/include/c++/v1'
    ARGV << '-isystem' << '/usr/include'

    unless ARGV.include? '-c' or ARGV.grep '\.pch$'
      ARGV << '-stdlib=libc++'
      ARGV << '-Wl,/usr/local/lib/libc++.dylib'
    end

    if BOOST
      ARGV << '-isystem' << "/usr/local/include/boost-#{BOOST}"

      ARGV.map! do |elem|
        if elem =~ /-lboost_([^-]+)$/
          if debug
            elem + "-clang-darwin-d-#{BOOST}"
          else
            elem + "-clang-darwin-#{BOOST}"
          end
        else
          elem
        end
      end
    end
  end

  ARGV << '-isystem' << '/usr/local/include'
  ARGV << '-isystem' << '/opt/local/include'

  unless ARGV.include? '-c' or ARGV.grep '\.pch$'
    ARGV << '-Wl,-L/usr/local/lib'
    ARGV << '-Wl,-L/opt/local/lib'
  end
end

if settings[:hosts]
  ARGV.unshift compiler
  compiler = 'distcc'
end

if ARGV.include?('-v')
  puts ENV, compiler, *ARGV
end

exec ENV, compiler, *ARGV

### cxx ends here
