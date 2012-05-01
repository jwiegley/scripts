#!/usr/bin/env ruby

compiler = 'clang++'

if ARGV.include?('--gcc')
  ARGV.delete('--gcc')
  ARGV << '--gcc48'
end

if ARGV.include?('--gcc42')
  ARGV.delete('--gcc')
  ARGV.delete('--gcc42')

  compiler = '/usr/bin/g++'

  ARGV << '-isystem' << '/usr/local/include/boost-1_49'

  ARGV.map! do |elem|
    if elem =~ /-lboost_([^-]+)$/
      elem + "-xgcc42-d-1_49"
    else
      elem
    end
  end

  ARGV << '-isystem' << '/opt/local/include'
  ARGV << '-isystem' << '/usr/local/include'

  ARGV << '-Wl,-L/opt/local/lib'
  ARGV << '-Wl,-L/usr/local/lib'

elsif ARGV.include?('--gcc47')
  ARGV.delete('--gcc')
  ARGV.delete('--gcc47')

  compiler = '/opt/local/bin/g++-mp-4.7'

  unless ARGV.include?('-std=c++03') or ARGV.include?('-std=c++11')
    ARGV << '-std=c++11'
  end

  ARGV << '-isystem' << '/usr/local/include/boost-1_49'

  ARGV.map! do |elem|
    if elem =~ /-lboost_([^-]+)$/
      elem + "-xgcc47-1_49"
    else
      elem
    end
  end

  ARGV << '-isystem' << '/usr/local/include'
  ARGV << '-isystem' << '/opt/local/include'

  ARGV << '-Wl,-L/usr/local/lib'
  ARGV << '-Wl,-L/opt/local/lib'

elsif ARGV.include?('--gcc48')
  ARGV.delete('--gcc')
  ARGV.delete('--gcc48')

  compiler = '/opt/local/bin/g++-mp-4.8'

  unless ARGV.include?('-std=c++03') or ARGV.include?('-std=c++11')
    ARGV << '-std=c++11'
  end

  ARGV << '-isystem' << '/usr/local/include/boost-1_49'

  ARGV.map! do |elem|
    if elem =~ /-lboost_([^-]+)$/
      elem + "-xgcc48-1_49"
    else
      elem
    end
  end

  ARGV << '-isystem' << '/usr/local/include'
  ARGV << '-isystem' << '/opt/local/include'

  ARGV << '-Wl,-L/usr/local/lib'
  ARGV << '-Wl,-L/opt/local/lib'

else
  if ARGV.include?('--clang30') or \
     (not ARGV.include?('-std=c++11') and not ARGV.include?('--clang31'))
    ARGV.delete('--clang30')

    compiler = '/usr/bin/clang++'

    ARGV << '-isystem' << '/opt/local/include'
    ARGV << '-isystem' << '/usr/local/include'

    ARGV << '-Wl,-L/opt/local/lib'
    ARGV << '-Wl,-L/usr/local/lib'
  else
    ARGV.delete('--clang')
    ARGV.delete('--clang31')

    compiler = '/usr/local/bin/clang++'

    unless ARGV.include?('-std=c++03')
      unless ARGV.include?('-std=c++11')
        ARGV << '-std=c++11'
      end
      ARGV << '-Qunused-arguments'
      ARGV << '-nostdlibinc'
      ARGV << '-isystem' << '/usr/local/include/c++/v1'
      ARGV << '-isystem' << '/usr/include'
      ARGV << '-stdlib=libc++'
      ARGV << '-Wl,/usr/local/lib/libc++.dylib'

      ARGV << '-isystem' << '/usr/local/include/boost-1_49'

      ARGV.map! do |elem|
        if elem =~ /-lboost_([^-]+)$/
          elem + "-clang-darwin-1_49"
        else
          elem
        end
      end
    end

    ARGV << '-isystem' << '/usr/local/include'
    ARGV << '-isystem' << '/opt/local/include'

    ARGV << '-Wl,-L/usr/local/lib'
    ARGV << '-Wl,-L/opt/local/lib'
  end
end

#puts compiler, *ARGV
exec compiler, *ARGV
