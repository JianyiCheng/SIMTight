#!/usr/bin/env python3

import sys
import os

def printUsage():
  print("Usage:")
  print("  sweep.py")
  print("    test          Test each config in simulation")
  print("    synth         Synthesise each config using quartus DSE")
  print("    bench         Run benchmarks on FPGA")

# Check args
if len(sys.argv) < 2:
  printUsage()
  sys.exit(-1)

# Various configs with different settings
config = {}
config["GCC"] = []
config["Clang"] = [("UseClang", "1")]
config["CHERI"] = config["Clang"] + [
    ("EnableTaggedMem", "1")
  , ("EnableCHERI", "1")
  ]
config["RegFileScalarisation"] = [
    ("SIMTEnableRegFileScalarisation", "1")
  , ("SIMTEnableAffineScalarisation", "1")
  , ("SIMTEnableCapRegFileScalarisation", "1")
  ]
config["ScalarUnit"] = config["RegFileScalarisation"] + [
    ("SIMTEnableScalarUnit", "1")
  ]
config["StoreBuffer"] = config["RegFileScalarisation"] + [
    ("SIMTEnableSVStoreBuffer", "1")
  ]
config["DynRegSpill"] = config["RegFileScalarisation"] + [
    ("SIMTRegFileSize", "512")
  , ("SIMTCapRegFileSize", "512")
  , ("SIMTUseSharedVecScratchpad", "1")
  ]
config["DynHalfRF"] = [
    ("SIMTEnableRegFileScalarisation", "1")
  , ("SIMTRegFilePreventScalarDetection", "1")
  , ("SIMTUseLRUSpill", "1")
  , ("SIMTRegFileSize", "1024")
  ]
config["StaticHalfRF"] = [
    ("UseRV32E", "1")
  ]

# Combinations of configs that are of interest
configCombos = [
    ["Clang"]
  , ["Clang", "StoreBuffer"]
  , ["Clang", "ScalarUnit"]
  , ["CHERI", "RegFileScalarisation"]
  , ["CHERI", "DynRegSpill"]
  , ["CHERI", "StoreBuffer"]
  , ["CHERI", "ScalarUnit"]
  # ["Clang", "DynRegSpill", "StoreBuffer", "ScalarUnit"]
  #, ["CHERI", "DynRegSpill", "StoreBuffer", "ScalarUnit"]
  ]

# Config combos of interest when benchmarking only
benchCombos = [
    ["GCC"]
  , ["GCC", "DynHalfRF"]
  , ["GCC", "StaticHalfRF"]
  ]

# Get directory containing script
scriptDir = os.path.dirname(os.path.realpath(__file__))

# Get dir containing repo
repoDir = os.path.dirname(scriptDir)

# Reset the repo to a clean state
def clean():
  os.chdir(repoDir)
  os.system("make clean > /dev/null")
  os.system("git checkout --quiet de10-pro/DE10_Pro.qsf")
  os.system("git checkout --quiet inc/Config.h")

# Apply settings to config file
def applySettings(combo):
  os.chdir(repoDir + "/scripts")
  for conf in combo:
    for setting in config[conf]:
      os.system("./modconf.py set " + setting[0] + " " + setting[1])

if sys.argv[1] == "test":
  # Remove old log file
  os.chdir(repoDir + "/test")
  os.system("rm -f test.log")
  # Test each combination in simulation
  for combo in configCombos:
    name = "Baseline" if combo == [] else "+".join(combo)
    clean()
    applySettings(combo)
    os.chdir(repoDir + "/test")
    os.system("echo >> test.log")
    os.system("echo ====== " + name + " ====== >> test.log")
    os.system("echo >> test.log")
    os.system("./test.sh >> test.log")
elif sys.argv[1] == "synth":
  # Remove old log file
  os.chdir(repoDir + "/de10-pro")
  os.system("rm -f synth.log")
  os.system("rm -rf Synth-*")
  # Synthesise each combination using quartus DSE
  for combo in configCombos:
    name = "Baseline" if combo == [] else "+".join(combo)
    print("Config: " + name)
    clean()
    applySettings(combo)
    # Run DSE
    os.chdir(repoDir + "/src")
    os.system("make > /dev/null")
    os.chdir(repoDir + "/de10-pro")
    os.system("./prepare_dse.sh")
    os.system('make many > /dev/null')
    # Save report
    os.system("echo >> synth.log")
    os.system("echo ====== " + name + " ====== >> synth.log")
    os.system("echo >> synth.log")
    os.system("make report | grep -v 'Info:' >> synth.log")
    os.system("mkdir -p Synth-" + name)
    os.system("find dse/*" +
              " | grep DE10_Pro.fit.place.rpt" +
              " | xargs -i cp --parents {} Synth-" + name)
  clean()
elif sys.argv[1] == "bench":
  # Remove old log file
  os.chdir(repoDir + "/test")
  os.system("rm -f bench.log")
  # Benchmark each combination in simulation
  for combo in (benchCombos + configCombos):
    name = "Baseline" if combo == [] else "+".join(combo)
    print("Config: " + name)
    clean()
    applySettings(combo)
    # Synthesise
    os.chdir(repoDir + "/src")
    os.system("make > /dev/null")
    os.chdir(repoDir + "/de10-pro") # Default to revD FPGA
    os.system("make one > /dev/null")
    # Run benchmarks
    os.chdir(repoDir + "/test")
    os.system("echo >> bench.log")
    os.system("echo ====== " + name + " ====== >> bench.log")
    os.system("echo >> bench.log")
    # Default to revD FPGA
    os.system("./test.sh --fpga-d --stats --apps-only >> bench.log")
else:
  printUsage()
  sys.exit(-1)
