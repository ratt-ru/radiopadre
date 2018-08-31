#!/usr/bin/env python

'''
Run script with desired B tables
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
from bokeh.models import Range1d, HoverTool, ColumnDataSource, LinearAxis, FixedTicker, Legend, Toggle, CustomJS, Title, CheckboxGroup, Select, Text
from bokeh.io import output_file, show, output_notebook, export_svgs
from bokeh.layouts import row, column, gridplot, widgetbox
from bokeh.models.widgets import Div



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
myms = options.myms
pngname = options.pngname



#uncomment next line for inline notebok output
#output_notebook()


if len(args) != 1:
	print 'Please specify a bandpass table to plot.'
	sys.exit(-1)
else:
	#to get the channels
	mytab = args[0].rstrip('/')
	spw_table= mytab+'/SPECTRAL_WINDOW'

if pngname == '':
	pngname = 'plot_'+mytab+'_corr'+str(corr)+'_'+doplot+'_field'+str(field)+'.html'

else:
	pngname = pngname + ".html"

output_file(pngname)


if doplot not in ['ap','ri']:
	print 'Plot selection must be either ap (amp and phase) or ri (real and imag)'
	sys.exit(-1)


#configuring the plot dimensions
PLOT_WIDTH = 700
PLOT_HEIGHT = 600


def make_plots(source, ax1 , ax2, color = 'purple', y1_err=None, y2_err=None):
	"""
		
	"""
	p1 = ax1.circle('x','y1',color=y1col,size=8, source=source, nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
	p1_err = errorbar(ax1, chans, y1, color=y1col, yerr=y1_err)
	p2 = ax2.circle('x','y2',color=y2col,size=8, source=source, nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
	p2_err = errorbar(ax2, chans, y2, color=y2col, yerr=y2_err)
	
	 
	return p1, p1_err, p2, p2_err

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


def color_denormalize(ycol):
	'''
		converting rgb values from 0 to 255

	'''
	ycol=np.array(ycol)
	ycol=np.array(ycol*255,dtype=int)
	ycol=ycol.tolist()
	ycol=tuple(ycol)[:-1]
	
	return ycol

def data_prep(masked_data, masked_data_err, doplot):
	"""

	preparing the data for plotting
	INPUTS:
	masked_data     : Flagged data from CPARAM column to be plotted. Masking takes care of the flagging
	masked_data_err : Flagged data from the PARAMERR column to be plotted 

	"""
	if doplot == 'ap':
		y1 = np.abs(masked_data)[0,:,corr]

		y1_err  = np.abs(masked_data_err)[0,:,corr]


		y2 = np.array(np.angle(masked_data[0,:,corr]))
		y2 = np.rad2deg(np.unwrap(y2))

		y2_err= np.array(np.angle(masked_data_err[0,:,corr]))
		y2_err = np.rad2deg(np.unwrap(y2_err))

	else:
		y1 = np.real(masked_data)[0,:,corr]
		y1_err = np.abs(masked_data_err)[0,:,corr]

		y2 = np.imag(masked_data)[0,:,corr]
		y2_err = None

	return y1, y1_err, y2, y2_err



tt = table(mytab,ack=False)
ants = np.unique(tt.getcol('ANTENNA1'))
fields = np.unique(tt.getcol('FIELD_ID'))

#getting the frequencies of the channels column
spw=table(spw_table, ack=False)
freqs = spw.getcol('CHAN_FREQ')[0]
spw.close()

#setting up colors for the antenna plots
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

if myms != '':
	anttab = table(myms.rstrip('/')+'/ANTENNA')
	antnames = anttab.getcol('NAME')
	anttab.done()
else:
	antnames = ''

#creating bokeh figures for plots	
TOOLS = dict(tools= 'box_select, box_zoom, reset, pan, save, wheel_zoom,lasso_select')
ax1 = figure(sizing_mode = 'scale_both', **TOOLS)
ax2 = figure(sizing_mode = 'scale_both', x_range=ax1.x_range, **TOOLS)

#setting up tooltips
hover=HoverTool(tooltips=[("(chans,y1)","($x,$y)")],mode='mouse')
hover.point_policy='snap_to_data'
hover2=HoverTool(tooltips=[("(chans,y2)","($x,$y)")],mode='mouse')
hover2.point_policy='snap_to_data'


#adding an extra x axis to contain channel frequencies
ax1.extra_x_ranges={"foo": Range1d(start=freqs[0]/1e9, end=freqs[-1]/1e9)}
linaxis = LinearAxis(x_range_name="foo", axis_label='Frequencies * 10^9',  major_label_orientation='horizontal')



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
	legend_err = "E"+str(ant)

	#creating colors for maps
	y1col = scalarMap.to_rgba(float(ant))
	y2col = scalarMap.to_rgba(float(ant))

	
	y1col = color_denormalize(y1col)
	y2col = color_denormalize(y2col)


	#from the table provided, get the antenna and the field ID columns
	mytaql = 'ANTENNA1=='+str(ant)+' && '
	mytaql+= 'FIELD_ID=='+str(field)


	subtab = tt.query(query=mytaql)
	cparam = subtab.getcol('CPARAM')
	flagcol = subtab.getcol('FLAG')
	#getting the number of channels
	nchan = cparam.shape[1]
	chans = np.arange(0,nchan,dtype='int')
	paramerr = subtab.getcol('PARAMERR')


	#masking the flagged channels and storing them into the masked data table.
	masked_data = np.ma.array(data=cparam,mask=flagcol)
	masked_data_err= np.array(np.ma.array(data=paramerr, mask=flagcol))
	

	if doplot == 'ap':

		y1, y1_err, y2, y2_err = data_prep(masked_data, masked_data_err, doplot)

		#setting up glyph data source
		source=ColumnDataSource(data=dict(x=chans,y1=y1,y2=y2))
		
		p1, p1_err, p2, p2_err = make_plots(source=source, color=y1col, ax1=ax1, ax2=ax2, y1_err=y1_err)

		ax1.yaxis.axis_label=ax1_ylabel='Amplitude'
		ax2.yaxis.axis_label=ax2_ylabel='Phase [Deg]'

	elif doplot == 'ri':

		y1, y1_err, y2, y2_err = data_prep(masked_data, masked_data_err, doplot)

		source = ColumnDataSource(data=dict(x=chans,y1=y1,y2=y2))

		p1, p1_err, p2, p2_err = make_plots(source=source, color=y1col, ax1=ax1, ax2=ax2, y1_err=y1_err)

		ax1.yaxis.axis_label=ax1_ylabel='Real'
		ax2.yaxis.axis_label=ax2_ylabel='Imaginary'

	#hide all the other plots until legend is clicked
	if ant>0:
		p1.visible=p2.visible=False

	#forming legend object items
	legend_items_ax1.append( (legend,[p1]) )
	legend_items_ax2.append( (legend,[p2]) )
	#for the errors
	legend_items_err_ax1.append( (legend_err, [p1_err]) )
	legend_items_err_ax2.append( (legend_err, [p2_err]) )
	
	subtab.close()

	
	if antnames == '':
		antlabel = str(ant)
	else:
		antlabel = antnames[ant]
	
	if np.min(chans) < xmin:
		xmin = np.min(chans)
	if np.max(chans) > xmax:
		xmax = np.max(chans)
	if np.min(y1) < yumin:
		yumin = np.min(y1)
	if np.max(y1) > yumax:
		yumax = np.max(y1)
	if np.min(y2) < ylmin:
		ylmin = np.min(y2)
	if np.max(y2) > ylmax:
		ylmax = np.max(y2)


#reorienting the min and max vales for x and y axes
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


#setting up the axes ranges
#ax2 ranges are controlled by ax1 ranges
ax1.y_range=Range1d(yumin,yumax)
ax2.y_range=Range1d(ylmin,ylmax)


ax1.xaxis.axis_label=ax1_xlabel='Channel'
ax2.xaxis.axis_label=ax2_xlabel='Channel'

tt.close()

#configuring titles for the plots
ax1_title = Title(text = ax1_ylabel + ' vs ' + ax1_xlabel, align='center', text_font_size='25px')
ax2_title = Title(text = ax2_ylabel + ' vs ' + ax2_xlabel, align='center', text_font_size='25px')



#LEGEND CONFIGURATIONS
BATCH_SIZE = 16
#determining the number of legend objects required to be created for each plot
num_legend_objs =  int( np.ceil( len(plotants) / float(BATCH_SIZE) ) )


#Automating creating batches of 16 each unless otherwise
#Looks like
# batch_0 : legend_items_ax1[:16]
#equivalent to
# batch_0 = legend_items_ax1[:16]
batches_ax1, batches_ax1_err, batches_ax2, batches_ax2_err = [], [], [], []

j = 0
for i in range(num_legend_objs):
    #incase the number is not a multiple of 16
    if i == num_legend_objs:
        batches_ax1.extend( [ legend_items_ax1[j:] ] )
        batches_ax2.extend( [ legend_items_ax2[j:] ] )
        batches_ax1_err.extend( [ legend_items_err_ax1[j:] ] )
        batches_ax2_err.extend( [ legend_items_err_ax2[j:] ] )
    else:
    	batches_ax1.extend( [ legend_items_ax1[j:j+BATCH_SIZE] ] )
        batches_ax2.extend( [ legend_items_ax2[j:j+BATCH_SIZE] ] )
        batches_ax1_err.extend( [ legend_items_err_ax1[j:j+BATCH_SIZE] ] )
        batches_ax2_err.extend( [ legend_items_err_ax2[j:j+BATCH_SIZE] ] )

    j+= BATCH_SIZE


#creating legend objects using items from the previous batches dictionary
#Legend objects allow their positioning outside the main plot
#resulting ordered dictionary looks like; 
# leg_0 : Legend(items=batch_0, location='top_right', click_policy='hide')
#equivalent to
# leg_0 = Legend(items=batch_0, location='top_right', click_policy='hide')

legend_objs_ax1, legend_objs_ax1_err, legend_objs_ax2, legend_objs_ax2_err = {}, {}, {}, {}

for i in range(num_legend_objs):
    legend_objs_ax1['leg_%s'%str(i)] = Legend(items=batches_ax1[i], location='top_right', click_policy='hide')
    legend_objs_ax2['leg_%s'%str(i)] = Legend(items=batches_ax2[i], location='top_right', click_policy='hide')
    legend_objs_ax1_err['leg_%s'%str(i)] = Legend(items=batches_ax1_err[i], location='top_right', click_policy='hide', visible = False)
    legend_objs_ax2_err['leg_%s'%str(i)] = Legend(items=batches_ax2_err[i], location='top_right', click_policy='hide', visible = False)


#adding legend objects to the layouts
for i in range(num_legend_objs):
	ax1.add_layout(legend_objs_ax1['leg_%s'%str(i)], 'right')
	ax2.add_layout(legend_objs_ax2['leg_%s'%str(i)], 'right')

	ax1.add_layout(legend_objs_ax1_err['leg_%s'%str(i)], 'right')
	ax2.add_layout(legend_objs_ax2_err['leg_%s'%str(i)], 'right')




#adding extra axes to the plots
ax1.add_layout(linaxis, 'above')

#adding plot titles
ax2.add_layout(ax2_title, 'above')
ax1.add_layout(ax1_title, 'above')


#adding hover tools to the plot
ax1.add_tools(hover)
ax2.add_tools(hover2)

#creating and configuring Antenna selection buttons
ant_select = Toggle(label='Select All Antennas', button_type='success', width=200)

#configuring toggle button for showing all the errors
toggle_err = Toggle(label='Show All Error bars', button_type='warning', width=200)

#Creating and configuring checkboxes
#Autogenerating checkbox labels
ant_labs = []
s= 0
e= BATCH_SIZE-1
for i in range(num_legend_objs):
    ant_labs.append("A%s - A%s"%(s,e))
    s = s + BATCH_SIZE
    e = e + BATCH_SIZE

batch_select = CheckboxGroup( labels = ant_labs, active = [])

#Dropdown to hide and show legends
legend_toggle = Select(title="Showing Legends: ", value = "alo", options = [("all","All"), ("alo","Antennas"), ("elo","Errors"),("non","None")])

ant_select.callback = CustomJS(args=dict(glyph1=legend_items_ax1, glyph2=legend_items_ax2, batchsel = batch_select), code=
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

	          	batchsel.active = []
	        }
	    else{
	            this.label='Deselect all Antennas';
	            for(i=0; i<glyph1.length; i++){
	                glyph1[i][1][0].visible = true;
	                glyph2[i][1][0].visible = true;
	      
	            }

	            batchsel.active = [0,1,2,3]
	        }
	'''
	 )



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


#BATCH SELECTION

batch_select.callback = CustomJS.from_coffeescript( args=dict(bax1 = batches_ax1, bax1_err = batches_ax1_err, bax2 = batches_ax2, bax2_err = batches_ax2_err, antsel =ant_select ), code="""
	
	#bax = [ [batch1], [batch2], [batch3] ]

	#j is batch number
	#i is glyph number
	j=0
	i=0

	if 0 in this.active
		i=0
		while i < bax1[j].length
			bax1[0][i][1][0].visible = true
			bax2[0][i][1][0].visible = true
			i++
	else
		i=0
		while i < bax1[0].length
			bax1[0][i][1][0].visible = false
			bax2[0][i][1][0].visible = false
			i++

	if 1 in this.active
		i=0
		while i < bax1[j].length
			bax1[1][i][1][0].visible = true
			bax2[1][i][1][0].visible = true
			i++
	else
		i=0
		while i < bax1[0].length
			bax1[1][i][1][0].visible = false
			bax2[1][i][1][0].visible = false
			i++
	
	if 2 in this.active
		i=0
		while i < bax1[j].length
			bax1[2][i][1][0].visible = true
			bax2[2][i][1][0].visible = true
			i++
	else
		i=0
		while i < bax1[0].length
			bax1[2][i][1][0].visible = false
			bax2[2][i][1][0].visible = false
			i++
	
	if 3 in this.active
		i=0
		while i < bax1[j].length
			bax1[3][i][1][0].visible = true
			bax2[3][i][1][0].visible = true
			i++
	else
		i=0
		while i < bax1[0].length
			bax1[3][i][1][0].visible = false
			bax2[3][i][1][0].visible = false
			i++


	if this.active.length == 4
		antsel.active = true
		antsel.label =  "Deselect all Antennas"
	else if this.active.length == 0
		antsel.active = false
		antsel.label = "Select all Antennas"
	""" )


legend_toggle.callback =CustomJS( args = dict(loax1 = legend_objs_ax1.values(), loax1_err = legend_objs_ax1_err.values(), loax2 = legend_objs_ax2.values(), loax2_err = legend_objs_ax2_err.values() ), code = """

	var len = loax1.length;
	var i ;
	if (this.value == "alo"){
		for(i=0; i<len; i++){
			loax1[i].visible = true;
			loax2[i].visible = true;
			
		}
	}

	else{
		for(i=0; i<len; i++){
			loax1[i].visible = false;
			loax2[i].visible = false;
			
		}
	}

	

	if (this.value == "elo"){
		for(i=0; i<len; i++){
			loax1_err[i].visible = true;
			loax2_err[i].visible = true;
			
		}
	}

	else{
		for(i=0; i<len; i++){
			loax1_err[i].visible = false;
			loax2_err[i].visible = false;
			
		}
	}	

	if (this.value == "all"){
		for(i=0; i<len; i++){
			loax1[i].visible = true;
			loax2[i].visible = true;
			loax1_err[i].visible = true;
			loax2_err[i].visible = true;
			
		}
	}

	if (this.value == "non"){
		for(i=0; i<len; i++){
			loax1[i].visible = false;
			loax2[i].visible = false;
			loax1_err[i].visible = false;
			loax2_err[i].visible = false;
			
		}
	}	



	""")

#uncomment next 2 line to save as svg also

'''
ax1.output_backend = "svg"
ax2.output_backend = "svg"
export_svgs([ax1], filename=pngname+".svg")
export_svgs([ax2], filename=pngname+".svg")
'''

plot_widgets = widgetbox([ant_select, batch_select, toggle_err, legend_toggle])
#figures   = column(ax1,ant_select, toggle_err)
#figures_b = column(ax2)

layout = gridplot([[plot_widgets, ax1, ax2]], plot_width=700, plot_height=600)
show(layout)
print 'Rendered: '+pngname
