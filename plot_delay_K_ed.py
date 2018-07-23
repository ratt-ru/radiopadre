#!/usr/bin/env python

'''
Run script with desired K tables
Requirement: bokeh
'''
from pyrap.tables import table
from optparse import OptionParser
import matplotlib.colors as colors
import matplotlib.cm as cmx
import glob
import pylab
import sys
import numpy as np

from bokeh.plotting import figure
from bokeh.models import Range1d, HoverTool, ColumnDataSource, LinearAxis, FixedTicker, Legend, Toggle, CustomJS
from bokeh.io import output_file, show, output_notebook, export_svgs
from bokeh.layouts import row, column, gridplot



parser = OptionParser(usage='%prog [options] tablename')
parser.add_option('-f','--field',dest='field',help='Field ID to plot (default = 1)',default=1)
parser.add_option('-d','--doplot',dest='doplot',help='Plot complex values as amp and phase (ap) or real and imag (ri) (default = ap)',default='ap')
parser.add_option('-a','--ant',dest='plotants',help='Plot only this antenna, or comma-separated list of antennas',default=[-1])
parser.add_option('-c','--corr',dest='corr',help='Correlation index to plot (usually just 0 or 1, default = 0)',default=0)
parser.add_option('--t0',dest='t0',help='Minimum time to plot (default = full range)',default=-1)
parser.add_option('--t1',dest='t1',help='Maximum time to plot (default = full range)',default=-1)
parser.add_option('--yu0',dest='yu0',help='Minimum y-value to plot for upper panel (default = full range)',default=-1)
parser.add_option('--yu1',dest='yu1',help='Maximum y-value to plot for upper panel (default = full range)',default=-1)
parser.add_option('--yl0',dest='yl0',help='Minimum y-value to plot for lower panel (default = full range)',default=-1)
parser.add_option('--yl1',dest='yl1',help='Maximum y-value to plot for lower panel (default = full range)',default=-1)
parser.add_option('--cmap',dest='mycmap',help='Matplotlib colour map to use for antennas (default = coolwarm)',default='coolwarm')
parser.add_option('--size',dest='mysize',help='Font size for figure labels (default = 20)',default=20)
parser.add_option('--ms',dest='myms',help='Measurement Set to consult for proper antenna names',default='')
parser.add_option('-p','--plotname',dest='pngname',help='Output PNG name (default = something sensible)',default='')
(options,args) = parser.parse_args()


field = int(options.field)
doplot = options.doplot
plotants = options.plotants
corr = int(options.corr)
t0 = float(options.t0)
t1 = float(options.t1)
yu0 = float(options.yu0)
yu1 = float(options.yu1)
yl0 = float(options.yl0)
yl1 = float(options.yl1)
mycmap = options.mycmap
mysize = int(options.mysize)
myms = options.myms
pngname = options.pngname



#uncomment next line for inline notebok output
#output_notebook()


if len(args) != 1:
	print 'Please specify a delay table to plot.'
	sys.exit(-1)
else:
	mytab = args[0].rstrip('/')

if pngname == '':
	pngname = 'plot_'+mytab+'_corr'+str(corr)+'_'+doplot+'_field'+str(field)+'.html'
	output_file(pngname)

#No complex data so this is generally ignored
if doplot != 'ap':
	print 'Plot selection must be ap '
	sys.exit(-1)


#configuring the plot dimensions
PLOT_WIDTH = 700
PLOT_HEIGHT = 600

def errorbar(fig, x, y, xerr=None, yerr=None, color='red', point_kwargs={}, error_kwargs={}):
	'''
	Function to plot the error bars for both x and y. 
	Takes in 3 compulsory parameters fig, x and y
	INPUT:
	============
	fig: the figure object
	x: x_axis
	y: y_axis
	xerr: errors for x axis, must be a list
	yerr: errors for y axis, must be a list
	color: color for the error bars


	OUTPUT
	==============
	Returns a multiline object for external legend rendering

	'''

	#setting default return value
	h= None
	if xerr is not None:

		x_err_x = []
		x_err_y = []
		for px, py, err in zip(x, y, xerr):
			x_err_x.append((px - err, px + err))
			x_err_y.append((py, py))
		h=fig.multi_line(x_err_x, x_err_y, color=color, line_width=3,level='underlay',visible=False,**error_kwargs)

	if yerr is not None:
		y_err_x = []
		y_err_y = []
		for px, py, err in zip(x, y, yerr):
			y_err_x.append((px, px))
			y_err_y.append((py - err, py + err))
		h=fig.multi_line(y_err_x, y_err_y, color=color, line_width=3, level='underlay',visible=False, **error_kwargs)
	
	fig.legend.click_policy='hide'

	return h



tt = table(mytab,ack=False)
#to plot all the data for all the antennas
antenna1=tt.getcol('ANTENNA1')
ants = np.unique(antenna1)

fields = np.unique(tt.getcol('FIELD_ID'))


#creating color scale for antenna 0 to 15
cNorm = colors.Normalize(vmin=0,vmax=len(ants)-1)
mymap = cm = pylab.get_cmap(mycmap)
scalarMap = cmx.ScalarMappable(norm=cNorm,cmap=mymap)



if int(field) not in fields.tolist():
	print 'Field ID '+str(field)+' not found'
	sys.exit(-1)

if plotants[0] != -1:
	plotants = plotants.split(',')
	for ant in plotants:
		if int(ant) not in ants:
			plotants.remove(ant)
			print 'Requested antenna ID '+str(ant)+' not found'
	if len(plotants) == 0:
		print 'No valid antennas indices requested'
		sys.exit(-1)
else:
	plotants = ants

#if reference ms is specified, the get the antenna names from there otherwise leave antenna names list empty
if myms != '':
	anttab = table(myms.rstrip('/')+'/ANTENNA')
	antnames = anttab.getcol('NAME')
	anttab.done()
else:
	antnames = ''


#creating bokeh figures for the plots
#viewing tools to be availed	
TOOLS = dict(tools= 'box_select, box_zoom, reset, pan, save, wheel_zoom,lasso_select')
ax1 = figure(plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT, **TOOLS)
ax2 = figure(plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT, x_range=ax1.x_range, **TOOLS)

#Configuring the axis data for the tooltips
hover=HoverTool(tooltips=[("(antenna1,y1)","($x,$y)")],mode='mouse')
hover.point_policy='snap_to_data'
hover2=HoverTool(tooltips=[("(antenna1,y2)","($x,$y)")],mode='mouse')
hover2.point_policy='snap_to_data'


#forming Legend object items for data and errors
legend_items_ax1 = []
legend_items_ax2 = []
legend_items_err_ax1 = []
legend_items_err_ax2 = []



xmin = 1e20
xmax = -1e20
ylmin = 1e20
ylmax = -1e20
yumin = 1e20
yumax = -1e20


#for each antenna
for ant in plotants:
	#creating legend labels
	legend     = "A"+str(ant)
	legend_err = "Err A"+str(ant)

	#creating colors for maps
	y1col = scalarMap.to_rgba(float(ant))
	y2col = scalarMap.to_rgba(float(ant))

	#denormalize rgba from 0-1 and convert to rgb (0-255)
	y1col=np.array(y1col)
	y1col=np.array(y1col*255,dtype=int)
	y1col=y1col.tolist()
	y1col=tuple(y1col)[:-1]



	y2col=np.array(y2col)
	y2col=np.array(y2col*255,dtype=int)
	y2col=y2col.tolist()
	y2col=tuple(y2col)[:-1]


	#from the table provided, get the antenna and the field ID columns
	mytaql = 'ANTENNA1=='+str(ant)+' && '
	mytaql+= 'FIELD_ID=='+str(field)

	subtab = tt.query(query=mytaql)
	antenna=subtab.getcol('ANTENNA1')
	fparam = subtab.getcol('FPARAM')
	flagcol = subtab.getcol('FLAG')
	paramerr = subtab.getcol('PARAMERR')

	masked_data = np.ma.array(data=fparam,mask=flagcol)
	masked_data_err = np.ma.array(data=paramerr,mask=flagcol)

	if doplot == 'ap':
		#for all the channels
		y1 = masked_data[:,0,corr]
		y1 = np.array(y1)
		y1_err= masked_data_err

		y2 = masked_data[:,0,1]
		y2 = np.array(y2)
		y2_err= masked_data_err

		#setting up glyph data source
		source=ColumnDataSource(data=dict(x=antenna,y1=y1,y2=y2))

		p1 = ax1.circle('x','y1',color=y1col,size=8, source=source, nonselection_color='#7D7D7D',nonselection_line_alpha=0.3)
		p1_err = errorbar(ax1, antenna, y1, color=y1col, yerr=y1_err)
		ax1.yaxis.axis_label = ax1_ylabel= 'Delay [Correlation 0]'

		p2 = ax2.circle('x','y2',color=y2col,size=8, source=source,  nonselection_color='#7D7D7D',nonselection_line_alpha=0.3)
		p2_err = errorbar(ax2, antenna, y2, color=y2col, yerr=y2_err)
		ax2.yaxis.axis_label = ax2_ylabel=  'Delay [Correlation 1]'

	elif doplot == 'ri':
		print "No complex values to plot"
		sys.exit()
	
	#hide all the other plots until legend is clicked
	if ant>0:
		p1.visible=p2.visible=False

	#forming legend object items
	legend_items_ax1.append( (legend,[p1]) )
	legend_items_ax2.append( (legend,[p2]) )
	legend_items_err_ax1.append( (legend_err, [p1_err]) )
	legend_items_err_ax2.append( (legend_err, [p2_err]) )
	
	subtab.close()

	
	if antnames == '':
		antlabel = str(ant)
	else:
		antlabel = antnames[ant]

	#setting minimum and maximum values for x, y1 and y2
	if np.min(ant) < xmin:
		xmin = np.min(ant)
	if np.max(ant) > xmax:
		xmax = np.max(ant)
	if np.min(y1) < yumin:
		yumin = np.min(y1)
	if np.max(y1) > yumax:
		yumax = np.max(y1)
	if np.min(y2) < ylmin:
		ylmin = np.min(y2)
	if np.max(y2) > ylmax:
		ylmax = np.max(y2)


xmin = xmin-4
xmax = xmax+4


if yumin < 0.0:
	yumin = -1*(1.1*np.abs(yumin))
else:
	yumin = yumin*0.9
yumax = yumax*1.1
if ylmin < 0.0:
	ylmin = -1*(1.1*np.abs(ylmin))
else:
	ylmin = ylmin*0.9
ylmax = ylmax*1.1

if t0 != -1:
	xmin = float(t0)
if t1 != -1:
	xmax = float(t1)
if yl0 != -1:
	ylmin = yl0
if yl1 != -1:
	ylmax = yl1
if yu0 != -1:
	yumin = yu0
if yu1 != -1:
	yumax = yu1


#ax2 ranges are controlled by ax1 ranges
ax1.y_range=Range1d(yumin,yumax)
ax2.y_range=Range1d(ylmin,ylmax)
	

ax1.xaxis.axis_label=ax1_xlabel='Antenna1'
ax2.xaxis.axis_label=ax2_xlabel='Antenna1'

ax1.title.text = ax1_ylabel + ' vs ' + ax1_xlabel
ax1.title.align='center'

ax2.title.text = ax2_ylabel + ' vs ' + ax2_xlabel
ax2.title.align='center'


#configuring click actions for legends
legend_ax1 = Legend(items=legend_items_ax1, location='top_right', click_policy='hide')
legend_err_ax1 = Legend(items=legend_items_err_ax1, location='top_right', click_policy='hide')
legend_ax2 = Legend(items=legend_items_ax2, location='top_right', click_policy='hide')
legend_err_ax2 = Legend(items=legend_items_err_ax2, location='top_right', click_policy='hide')


#adding legends to the plots
ax1.add_layout(legend_ax1, 'right')
ax2.add_layout(legend_ax2, 'right')
ax1.add_layout(legend_err_ax1, 'right')
ax2.add_layout(legend_err_ax2, 'right')


#configuring click actions for legends and adding tooltips to the plots
ax1.add_tools(hover)
ax2.add_tools(hover2)

toggle= Toggle(label='Select All Antennas', button_type='success', width=200)
toggle.callback = CustomJS(args=dict(glyph1=legend_items_ax1, glyph2=legend_items_ax2), code=
	'''
		var i;
		 //if toggle button active
	    if (this.active==false)
	        {
	            this.label='Select all Antennas';
	            
	            
	            for(i=0; i<glyph1.length; i++){
	                glyph1[i][1][0].visible = false;
	                glyph2[i][1][0].visible = false;
	            }
	        }
	    else{
	            this.label='Deselect all Antennas';
	            for(i=0; i<glyph1.length; i++){
	                glyph1[i][1][0].visible = true;
	                glyph2[i][1][0].visible = true;
	      
	            }
	        }
	'''
	 )



#configuring toggle button for showing all the errors
toggle_err = Toggle(label='Show All Error bars', button_type='warning', width=200)
toggle_err.callback = CustomJS(args=dict(err1=legend_items_err_ax1, err2=legend_items_err_ax2), code='''
		var i;
		 //if toggle button active
	    if (this.active==false)
	        {
	            this.label='Show All Error bars';
	            
	            
	            for(i=0; i<err1.length; i++){
	                err1[i][1][0].visible = false;
	                //checking for error on phase and imaginary planes as these tend to go off
	                if (err2[i][1][0]){
	                	err2[i][1][0].visible = false;
	                }
	                
	            }
	        }
	    else{
	            this.label='Hide All Error bars';
	            for(i=0; i<err1.length; i++){
	                err1[i][1][0].visible = true;
	                if (err2[i][1][0]){
	                	err2[i][1][0].visible = true;
	                }
	            }
	        }
	       
	''')



#uncomment next 2 line to save as svg also
'''
ax1.output_backend = "svg"
ax2.output_backend = "svg"
export_svgs([ax1], filename=pngname+".svg")
export_svgs([ax1], filename=pngname+"b.svg")'
'''
figures   = column(ax1,toggle, toggle_err)
figures_b = column(ax2)

layout = gridplot([[figures,figures_b]], plot_width=700, plot_height=600)
show(layout)

print 'Rendered: '+pngname
