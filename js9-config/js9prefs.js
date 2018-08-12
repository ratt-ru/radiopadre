var JS9Prefs = {
  "globalOpts": {"helperType":	     "nodejs",
  		 "helperPort":       2718, 
		 "helperCGI":        "./cgi-bin/js9/js9Helper.cgi",
		 "fits2png":         false,
		 "debug":	     0,
		 "loadProxy":	     true,
		 "workDir":	     "./tmp",
		 "workDirQuota":     1000,
		"fits2fits":        "size>50",
		"image":
		{
		  "xdim": 2048,
		  "ydim": 2048,
		  "bin":  2
		},
		 "dataPath":	     "$HOME/Desktop:$HOME/data",
		 "analysisPlugins":  "./analysis-plugins",
		 "analysisWrappers": "./analysis-wrappers",
		 "requireHelper":    true,
		 "intensivePlugins": true,
		 "htimeout": 10000,
		 "lhtimeout": 10000
		 },
  "imageOpts":  {"colormap":	     "grey",
  		 "scale":     	     "linear"}
}
