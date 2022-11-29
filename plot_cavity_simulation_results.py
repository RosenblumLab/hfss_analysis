import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np

sns.set_theme()

"""
   ################################################
   # --------------- two data sets ---------------#
   ################################################
"""

df1 = pd.read_csv('height_sweep3_HFSSDesign2.csv', sep=',')
df2 = pd.read_csv('height_sweep3_HFSSDesign3.csv', sep=',')

"""
# both data sets on the same plot
"""

ax = df1.plot(x='Cavity height change', y='Cavity Quality Factor', figsize=(5, 5), marker='o', kind='line')
df2.plot(x='Cavity height change', y='Cavity Quality Factor', ax=ax, marker='o', kind='line')

fig, ax = plt.subplots()

ax.plot(list(df1["Cavity height change"]), list(df1["Cavity Quality Factor"]), marker='o')
ax.plot(list(df2["Cavity height change"]), list(df2["Cavity Quality Factor"]), marker='o')

# and then set to log scale
ax.set(yscale="log")
plt.legend(loc='upper left', labels=['old cavity', 'new cavity'])

"""
# two separate plots
"""

plot = sns.relplot(data=df1, x='Cavity height change', y='Cavity Quality Factor', color='b', marker='o', kind='line')
plot = sns.relplot(data=df2, x='Cavity height change', y='Cavity Quality Factor', color='orange', marker='o', kind='line')
#
plot.set(yscale="log")

"""
########################################################################
"""

# plt.xticks(rotation=30)
# yticks_numbers = [6e10, 1e11, 1.5e11, 2e11, 2.5e11, 3e11]
# yticks_labels = []
# for i in yticks_numbers:
#     scientific_notation = "{:.1e}".format(i)
#     yticks_labels.append(str(scientific_notation))
#
# plt.yticks(yticks_numbers, yticks_labels)
# #
# plt.subplots_adjust(left=0.20, bottom=0.20)
#
# plt.title('Change in Simulated Cavity Quality Factor')
# # plt.legend(loc='upper left', labels=['old cavity', 'new cavity'])
# plt.ylabel('Quality factor')
# plt.xlabel('Cavity height change')
#
# plt.show()

"""
   ###################################################################
   # --------------- draw one graph with one data set ---------------#
   ###################################################################
"""

df1 = pd.read_csv('NEW_rod_height_sweep3_11_15_05_HFSSDesign3.csv', sep=',')

plot = sns.relplot(data=df1, x='Cavity rod height', y='Cavity Quality Factor', color='b', marker='o', kind='line')

plot.set(yscale="log")

plt.xticks(rotation=30)
yticks_numbers = np.arange(0.5e11, 5e11, step=0.5e11)
yticks_labels = []
for i in yticks_numbers:
    scientific_notation = "{:.1e}".format(i)
    yticks_labels.append(str(scientific_notation))

plt.yticks(yticks_numbers, yticks_labels)

plt.subplots_adjust(left=0.20, bottom=0.20)

plt.title('New design')
plt.ylabel('Quality factor')

plt.show()

"""
##################################################################################
"""

# ax = df1.plot(x='Cavity height change', y='Cavity Quality Factor', figsize=(5, 5), marker='o', kind='line')
# df2.plot(x='Cavity height change', y='Cavity Quality Factor', ax=ax, marker='o', kind='line')
# # and then set to log scale
# ax.set(yscale="log")
# plt.legend(loc='upper left', labels=['old cavity', 'new cavity'])