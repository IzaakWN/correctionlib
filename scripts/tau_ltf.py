#! /usr/bin/env python3
# Author: Izaak Neutelings (January 2021)
# Description: Script to play around with format of TauPOG SFs.
# Instructions:
#  ./scripts/test.py
# Sources:
#   https://github.com/cms-tau-pog/TauIDSFs/blob/master/utils/createSFFiles.py
#   https://github.com/cms-nanoAOD/correctionlib/blob/master/tests/test_core.py
#   https://cms-nanoaod-integration.web.cern.ch/integration/master-106X/mc102X_doc.html#Tau
import sys; sys.path.append('scripts')
from utils import *


def makecorr_ltf(sfs=None,**kwargs):
  """e -> tauh fake rate SF"""
  verb   = kwargs.get('verb',0)
  outdir = kwargs.get('outdir',"data/tau")
  ltype  = kwargs.get('ltype','e')[0]
  allgms = [0,1,2,3,4,5,6] # all allowed genmatches
  if 'e' in ltype: # e -> tauh
    ebins = [0.0,1.460,1.558,2.3] # eta bins
    gms   = [1,3]
  else: # mu -> tauh
    ltype = "mu"
    ebins = [0.0,0.4,0.8,1.2,1.7,2.3] # eta bins
    gms   = [2,4]
  if sfs:
    id    = kwargs.get('id',   "unkown")
    era   = kwargs.get('era',  "unkown")
    name  = kwargs.get('name', f"tau_sf_dm_{id}_{era}")
    fname = kwargs.get('fname',f"{outdir}/{name}.json")
    info  = kwargs.get('info', f"DM-dependent SFs for {id} in {era}")
    ebins = kwargs.get('bins', ebins)
    wps   = list(sfs.keys())
  else: # test format with dummy values
    id    = kwargs.get('id',  "DeepTau2017v2p1VSjet")
    header(f"Dummy {id} SFs for test")
    name  = kwargs.get('name', f"test_{id}_dm")
    fname = kwargs.get('fname',f"{outdir}/test_tau_{ltype}tf.json")
    info  = kwargs.get('info', f"DM-dependent SFs for {id}")
    ebins = kwargs.get('bins', ebins)
    wps   = [
      #'VVVLoose', 'VVLoose', 'VLoose',
      'Loose', 'Medium', 'Tight',
      #'VTight', 'VVTight'
    ]
    sfs   = {wp: [(1.0,1.1,0.9) for s in range(len(ebins)-1)] for wp in wps}
  wps.sort(key=wp_sortkey)
  print(f">>> etabins={ebins}")
  
  # LTF DATA
  ltfdata = {
    'nodetype': 'category', # category:wp
    'input': "wp",
    'content': [ # key:wp
      { 'key': wp, # key:wp==wp
        'value': {
          'nodetype': 'transform', # transform:eta
          'input': "eta",
          'rule': {
            'nodetype': 'formula',
            'expression': "abs(x)",
            'parser': "TFormula",
            'variables': ["eta"],
          },
          'content': {
            'nodetype': 'binning', # binning:eta
            'input': "eta",
            'edges': ebins,
            'flow': "clamp", # do
            'content': [ # bin:eta
              { 'nodetype': 'category', # category:syst
                'input': "syst",
                'content': [ # key:syst
                  { 'key': 'nom',  'value': bin[0] }, # central
                  { 'key': 'up',   'value': bin[1] }, # up
                  { 'key': 'down', 'value': bin[2] }, # down
                ] # key:syst
              } for bin in sfs[wp]
            ] # bin:eta
          } # binning:eta
        } # transform:eta
      } for wp in wps # key:wp==wp
    ] # key:wp
  } # category:wp
  
  # CORRECTION OBJECT
  corr  = Correction.parse_obj({
    'version': 0,
    'name': f"DeepTau2017v2p1VS{ltype}_test",
    'description': f"{ltype} -> tau_h fake rate SFs for DeepTau2017v2p1VS{ltype}",
    'inputs': [
      {'name': "eta",      'type': "real",   'description': "Reconstructed tau eta"},
      {'name': "genmatch", 'type': "int",    'description': getgminfo()},
      {'name': "wp",       'type': "string", 'description': getwpinfo(id,wps)},
      {'name': "syst",     'type': "string", 'description': getsystinfo()},
    ],
    'output': {'name': "weight", 'type': "real"},
    'data': { # category:genmatch -> category:wp -> transform:eta -> binning:eta -> category:syst
      #'nodetype': 'transform', # transform:eta
      #'input': "genmatch",
      #'rule': {
      #  'nodetype': 'category', # category:genmatch
      #  'input': "genmatch",
      #  'default': 0, # everything else
      #  'content': [ # key:genmatch
      #    { 'key': gm,   'value': gm }, # l -> tau_h, prompt
      #    { 'key': gm+2, 'value': gm }, # l -> tau_h, tau decay
      #  ] # key:genmatch
      #}, # category:genmatch
      #'content': {
        'nodetype': 'category', # category:genmatch
        'input': "genmatch",
        #'default': 1.0, # no default: throw error if unrecognized genmatch
        'content': [ # key:genmatch
          { 'key': gm,
            'value': ltfdata if gm in gms else 1.0
          } for gm in allgms
        ] # key:genmatch
    } # category:genmatch
    #} # transform:genmatch
  })
  if verb>1:
    print(JSONEncoder.dumps(corr))
  elif verb>0:
    print(corr)
  if fname:
    print(f">>> Writing {fname}...")
    JSONEncoder.write(corr,fname)
  return corr
  

def evaluate(corrs):
  header("Evaluate")
  cset_py, cset = wrap(corrs) # wrap to create C++ object that can be evaluated
  ebins = [-2.0,-1.0,0.0,1.1,2.0,2.5,3.0]
  gms   = [0,1,2,3,4,5,6,7]
  for name in list(cset):
    corr = cset[name]
    print(f">>>\n>>> {name}: {corr.description}")
    wp   = 'Tight'
    print(f">>>\n>>> WP={wp}")
    print(">>> %8s"%("genmatch")+" ".join("  %-15.1f"%(e) for e in ebins))
    for gm in gms:
      row = ">>> %8d"%(gm)
      for eta in ebins:
        sfnom = 0.0
        for syst in ['nom','up','down']:
          #print(">>>   gm=%d, eta=%4.1f, syst=%r sf=%s"%(gm,eta,syst,eval(corr,eta,gm,wp,syst)))
          try:
            sf = corr.evaluate(eta,gm,wp,syst)
            if 'nom' in syst:
              row += "%6.2f"%(sf)
              sfnom = sf
            elif 'up' in syst:
              row += "%+6.2f"%(sf-sfnom)
            else:
              row += "%+6.2f"%(sf-sfnom)
          except Exception as err:
            row += "\033[1m\033[91m"+"  ERR".ljust(6)+"\033[0m"
      print(row)
  print(">>>")
  

def main():
  corr1 = makecorr_ltf(ltype='e')
  corr2 = makecorr_ltf(ltype='m')
  corrs = [corr1,corr2] # list of corrections
  evaluate(corrs)
  #write(corrs)
  #read(corrs)
  

if __name__ == '__main__':
  main()
  print()
  
