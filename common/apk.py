import os
import subprocess
import glob
import hashlib
import shutil
from common.basedir import BASEDIR
from selfdrive.swaglog import cloudlog
from common.params import Params, put_nonblocking
params = Params()

#android_packages = ("com.google.android.inputmethod.korean", "com.mixplorer", "com.rhmsoft.edit.pro", "kr.mappers.AtlanSmart", "kt.navi", "com.skt.tmap.ku", "com.locnall.KimGiSa", "com.gmd.hidesoftkeys", "ai.comma.plus.offroad")
android_packages = ("com.google.android.inputmethod.korean", "com.mixplorer", "com.rhmsoft.edit.pro", "com.skt.tmap.ku", "com.gmd.hidesoftkeys", "ai.comma.plus.offroad")

def get_installed_apks():
  dat = subprocess.check_output(["pm", "list", "packages", "-f"], encoding='utf8').strip().split("\n")
  ret = {}
  for x in dat:
    if x.startswith("package:"):
      v, k = x.split("package:")[1].split("=")
      ret[k] = v
  return ret

def install_apk(path):
  # can only install from world readable path
  install_path = "/sdcard/%s" % os.path.basename(path)
  shutil.copyfile(path, install_path)

  ret = subprocess.call(["pm", "install", "-r", install_path])
  os.remove(install_path)
  return ret == 0

def start_offroad():
  set_package_permissions()

  system("pm disable com.mixplorer")
  system("pm disable com.rhmsoft.edit.pro")
  system("pm disable com.skt.tmap.ku")
  system("pm disable com.gmd.hidesoftkeys")
  opkr_boot_softkey = True if params.get("OpkrBootSoftkey", encoding='utf8') == "1" else False
  opkr_boot_tmap = True if params.get("OpkrBootTmap", encoding='utf8') == "1" else False

  system("am start -n ai.comma.plus.offroad/.MainActivity")

  if opkr_boot_softkey:
    system("pm enable com.gmd.hidesoftkeys")
    system("am start -n com.gmd.hidesoftkeys/com.gmd.hidesoftkeys.MainActivity")

  if opkr_boot_tmap:
    if not opkr_boot_softkey:
      system("pm enable com.gmd.hidesoftkeys")
      system("am start -n com.gmd.hidesoftkeys/com.gmd.hidesoftkeys.MainActivity")
    system("pm enable com.skt.tmap.ku")
    system("am start -n com.skt.tmap.ku/com.skt.tmap.activity.TmapNaviActivity")
    

def set_package_permissions():
  pm_grant("ai.comma.plus.offroad", "android.permission.ACCESS_FINE_LOCATION")
  pm_grant("ai.comma.plus.offroad", "android.permission.READ_PHONE_STATE")
  pm_grant("ai.comma.plus.offroad", "android.permission.READ_EXTERNAL_STORAGE")
  appops_set("ai.comma.plus.offroad", "SU", "allow")
  appops_set("ai.comma.plus.offroad", "WIFI_SCAN", "allow")

def appops_set(package, op, mode):
  system(f"LD_LIBRARY_PATH= appops set {package} {op} {mode}")

def pm_grant(package, permission):
  system(f"pm grant {package} {permission}")

def system(cmd):
  try:
    cloudlog.info("running %s" % cmd)
    subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
  except subprocess.CalledProcessError as e:
    cloudlog.event("running failed",
      cmd=e.cmd,
      output=e.output[-1024:],
      returncode=e.returncode)

# *** external functions ***

def update_apks():
  # install apks
  installed = get_installed_apks()

  install_apks = glob.glob(os.path.join(BASEDIR, "apk/*.apk"))
  for apk in install_apks:
    app = os.path.basename(apk)[:-4]
    if app not in installed:
      installed[app] = None

  cloudlog.info("installed apks %s" % (str(installed), ))

  for app in installed.keys():
    apk_path = os.path.join(BASEDIR, "apk/"+app+".apk")
    if not os.path.exists(apk_path):
      continue

    h1 = hashlib.sha1(open(apk_path, 'rb').read()).hexdigest()
    h2 = None
    if installed[app] is not None:
      h2 = hashlib.sha1(open(installed[app], 'rb').read()).hexdigest()
      cloudlog.info("comparing version of %s  %s vs %s" % (app, h1, h2))

    if h2 is None or h1 != h2:
      cloudlog.info("installing %s" % app)

      success = install_apk(apk_path)
      if not success:
        cloudlog.info("needing to uninstall %s" % app)
        system("pm uninstall %s" % app)
        success = install_apk(apk_path)

      assert success

def pm_apply_packages(cmd):
  for p in android_packages:
    system("pm %s %s" % (cmd, p))

if __name__ == "__main__":
  update_apks()
