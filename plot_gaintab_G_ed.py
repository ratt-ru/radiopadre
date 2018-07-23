#!/usr/bin/env python
'''
Run script with desired G tables
Requirement: bokeh
'''


from pyrap.tables import table
from optparse import OptionParser
import matplotlib.colors as colors #matplotlib normalizer
import matplotlib.cm as cmx #the matplotblib clormap used in conjuction with the color normalizer
import glob
import pylab	#for imaging
import sys
import numpy as np

from bokeh.plotting import figure
from bokeh.models import Range1d, HoverTool, ColumnDataSource, LinearAxis, FixedTicker, Legend, Toggle, CustomJS
from bokeh.io import output_file, show, output_notebook, export_svgs
from bokeh.layouts import row, column, gridplot


parser = OptionParser(usage='%prog [options] tablename')
parser.add_option('-f','--field',dest='field',help='Field ID to plot (default = 0)',default=0)
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
	print 'Please specify a gain table to plot.'
	sys.exit(-1)
else:
	#getting the name of the gain table specified
	mytab = args[0].rstrip('/')


if pngname == '':
	pngname = 'plot_'+mytab+'_corr'+str(corr)+'_'+doplot+'_field'+str(field)+'.html'
	output_file(pngname)
else:
	output_file(pngname)


#by default is ap: amplitude and phase
if doplot not in ['ap','ri']:
	print 'Plot selection must be either ap (amp and phase) or ri (real and imag)'
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


#open the table using the tt object and perform operations on it
#ack: print message to show if table was opened succssfully

tt = table(mytab,ack=False)
ants = np.unique(tt.getcol('ANTENNA1'))
fields = np.unique(tt.getcol('FIELD_ID'))
flags = tt.getcol('FLAG')


#setting up colors for the antenna plots
cNorm = colors.Normalize(vmin=0,vmax=len(ants)-1)
mymap = cm = pylab.get_cmap(mycmap)
scalarMap = cmx.ScalarMappable(norm=cNorm,cmap=mymap)


if int(field) not in fields.tolist():
	print 'Field ID '+str(field)+' not found'
	sys.exit(-1)

if plotants[0] != -1:
	#creating a list for the antennas to be plotted
	plotants = plotants.split(',')

	for ant in plotants:
		if int(ant) not in ants:
			plotants.remove(ant)
			print 'Requested antenna ID '+str(ant)+' not found'
	if len(plotants) == 0:
		print 'No valid antennas have been requested'
		sys.exit(-1)
	else:
		plotants = np.array(plotants,dtype=int)
else:
	plotants = ants

if myms != '':
	anttab = table(myms.rstrip('/')+'/ANTENNA')
	antnames = anttab.getcol('NAME')
	anttab.done()
else:
	antnames = ''


#creating bokeh figures for plots	
#linking plots ax1 and ax2 via the x_axes because fo similarities in range
TOOLS = dict(tools= 'box_select, box_zoom, reset, pan, save, wheel_zoom,lasso_select')
ax1=figure(plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT, **TOOLS)
ax2=figure(plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT, x_range=ax1.x_range, **TOOLS)

hover=HoverTool(tooltips=[("(time,y1)","($x,$y)")],mode='mouse')
hover.point_policy='snap_to_data'
hover2=HoverTool(tooltips=[("(time,y2)","($x,$y)")],mode='mouse')
hover2.point_policy='snap_to_data'


#forming Legend object items for data and errors
legend_items_ax1 = []
legend_items_ax2 = []
legend_items_err_ax1 = []
legend_items_err_ax2 = []


#setting default maximum and minimum values for the different axes
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

	#denormalizing the color array
	y1col=np.array(y1col)
	y1col=np.array(y1col*255,dtype=int)
	y1col=y1col.tolist()
	y1col=tuple(y1col)[:-1]



	y2col=np.array(y2col)
	y2col=np.array(y2col*255,dtype=int)
	y2col=y2col.tolist()
	y2col=tuple(y2col)[:-1]

	
	mytaql = 'ANTENNA1=='+str(ant)
	#mytaql+= '&&FIELD_ID=='+str(field)

	#querying the table for the 2 columns
	#getting data from the antennas, cparam contains the correlated data, time is the time stamps
	
	subtab = tt.query(query=mytaql)
	#Selecting values from the table for antenna ants
	cparam = subtab.getcol('CPARAM')
	flagcol = subtab.getcol('FLAG')
	times = subtab.getcol('TIME')
	paramerr = subtab.getcol('PARAMERR')

	#Referencing time wrt the initial time
	times = times - times[0]
	#creating a masked array to prevent invalid values from being computed. IF mask is true, then the element is masked, an dthus won't be used in the calculation
	#removing flagged data from cparams
	masked_data = np.ma.array(data=cparam,mask=flagcol)
	masked_data_err= np.array(np.ma.array(data=paramerr, mask=flagcol))

	

	if doplot == 'ap':
		y1 = np.abs(masked_data)[:,0,corr]
		y1_err= np.abs(masked_data_err)[:,0,corr]

	
		y2 = np.angle(masked_data)[:,0,corr]
		#y2 = np.array(y2[:,corr])
		#remove phase limit from -pi to pi
		y2 = np.unwrap(y2)
		y2 = np.rad2deg(y2)
		#y2_err = 

		#setting up glyph data source
		source=ColumnDataSource(data=dict(x=times, y1=y1, y2=y2))
		
		p1 = ax1.circle('x','y1',size=8,alpha=1, color=y1col,source=source, nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
		p1_err = errorbar(ax1, times, y1, color=y1col, yerr=y1_err)
		ax1.yaxis.axis_label=ax1_ylabel='Amplitude'

		p2 = ax2.circle('x','y2',size=8,alpha=1, color=y2col, source=source,  nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
		p2_err = errorbar(ax1, times, y1, color=y1col)
		ax2.yaxis.axis_label=ax2_ylabel='Phase [Deg]'

	elif doplot == 'ri':
		y1 = np.real(masked_data)[:,0,corr]
		y1_err= np.abs(masked_data_err)[:,0,corr]

		y2 = np.imag(masked_data)[:,0,corr]
		#y2_err = None
		
		source=ColumnDataSource(data=dict(x=times, y1=y1, y2=y2))

		p1 = ax1.circle('x','y1',size=8,alpha=1, color=y1col,source=source, nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
		p1_err = errorbar(ax1, times, y1, color=y1col, yerr=y1_err)
		ax1.yaxis.axis_label=ax1_ylabel='Real'
	

		#no errror because error value is real
		p2 = ax2.circle('x','y2',size=8,alpha=1, color=y2col,source=source, nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
		p2_err = errorbar(ax2, times, y2, color=y2col)
		ax2.yaxis.axis_label=ax2_ylabel='Imaginary'

	#hide all the other plots until legend is clicked
	if ant>0:
		p1.visible=p2.visible=False
		

	#forming legend object items
	legend_items_ax1.append( (legend,[p1]) )
	legend_items_ax2.append( (legend,[p2]) )
	legend_items_err_ax1.append( (legend_err, [p1_err]) )
	legend_items_err_ax2.append( (legend_err, [p2_err]) )
	

	subtab.close()

	#dx = 1.0/float(len(ants)-1)
	if antnames == '':
		antlabel = str(ant)
	else:
		antlabel = antnames[ant]

	if np.min(times) < xmin:
		xmin = np.min(times)
	if np.max(times) > xmax:
		xmax = np.max(times)
	if np.min(y1) < yumin:
		yumin = np.min(y1)
	if np.max(y1) > yumax:
		yumax = np.max(y1)
	if np.min(y2) < ylmin:
		ylmin = np.min(y2)
	if np.max(y2) > ylmax:
		ylmax = np.max(y2)


#reorienting the min and max vales for x and y axes
xmin = xmin-400
xmax = xmax+400


#setting the axis limits for scaliing
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



ax1.y_range=Range1d(yumin,yumax)
ax2.y_range=Range1d(ylmin,ylmax)


ax1.xaxis.axis_label = ax1_xlabel='Time [s]'
ax2.xaxis.axis_label = ax2_xlabel='Time [s]'

#configuring both figure titles (font size and alignment)
'''ax1.title.text = ax1_ylabel + ' vs ' + ax1_xlabel
ax1.title.align='center'
ax1.title.text_font_size='25px'''

ax2.title.text = ax2_ylabel + ' vs ' + ax2_xlabel
ax2.title.align='center'
ax2.title.text_font_size='25px'


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

'''ax1.output_backend = "svg"
ax2.output_backend = "svg"
export_svgs([ax1], filename=pngname+".svg")
export_svgs([ax1], filename=pngname+"b.svg")'''



figures   = column(ax1,toggle, toggle_err)
figures_b = column(ax2)

layout = gridplot([[figures,figures_b]], plot_width=700, plot_height=600)
show(layout)
print 'Rendered: '+pngname
