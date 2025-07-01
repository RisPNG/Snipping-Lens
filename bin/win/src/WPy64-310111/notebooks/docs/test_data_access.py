# pyodbc 
import pyodbc

# look for pyodbc providers
sources = pyodbc.dataSources()
dsns = list(sources.keys())
sl = ['    %s [%s]' % (dsn, sources[dsn]) for dsn in dsns]
print("pyodbc Providers: (beware 32/64 bit driver and python version must match)\n", '\n'.join(sl))

# odbc to EXCEL .xls via pyodbc (beware 32/64 bit driver and pytho version must match)
import pyodbc, os
filename = os.path.join(os.getcwd(), 'test.xls')
todo = "select * from [Sheet1$]"
print("\nusing pyodbc to read an Excel .xls file:\n\t", filename)
if os.path.exists(filename):
    CNXNSTRING = 'Driver={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};DBQ=%s;READONLY=FALSE' % filename
    try:
        cnxn = pyodbc.connect(CNXNSTRING, autocommit=True)
        cursor = cnxn.cursor()
        rows = cursor.execute(todo).fetchall()
        print([column[0] for column in cursor.description])
        print(rows)
        cursor.close()
        cnxn.close()
    except:
        print("\n *** failed ***\n")
# odbc to ACCESS .mdb via pyodbc (beware 32/64 bit driver and python version must match)
import pyodbc, os
filename = os.path.join(os.getcwd(), 'test.mdb')
print("\nusing pyodbc to read an ACCESS .mdb file:\n\t", filename)
if os.path.exists(filename):
    CNXNSTRING = 'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;READONLY=FALSE' % filename
    try:
        cnxn = pyodbc.connect(CNXNSTRING, autocommit=False)
        cursor = cnxn.cursor()
        rows = cursor.execute("select *  from users").fetchall()
        print([column[0] for column in cursor.description])
        print(rows)
        cursor.close()
        cnxn.close()
    except:
        print("\n *** failed ***\n")
    
# pythonnet
import clr
clr.AddReference("System.Data")
import System.Data.OleDb as ADONET
import System.Data.Odbc as ODBCNET
import System.Data.Common as DATACOM

table = DATACOM.DbProviderFactories.GetFactoryClasses()
print("\n .NET Providers: (beware 32/64 bit driver and pytho version must match)")
for  row in table.Rows:
    print("   %s" % row[table.Columns[0]])
    print("      ",[row[column] for column in table.Columns if column != table.Columns[0]])

    
# odbc to EXCEL .xls via pythonnet
import clr, os
clr.AddReference("System.Data")
import System.Data.OleDb as ADONET
import System.Data.Odbc as ODBCNET
import System.Data.Common as DATACOM

filename = os.path.join(os.getcwd(), 'test.xls')
todo = "select * from [Sheet1$]"
print("\nusing pythonnet to read an excel .xls file:\n\t", filename , "\n\t", todo)
if os.path.exists(filename):
    CNXNSTRING = 'Driver={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};DBQ=%s;READONLY=FALSE' % filename
    cnxn = ODBCNET.OdbcConnection(CNXNSTRING)
    try:
        cnxn.Open()
        command = cnxn.CreateCommand()
        command.CommandText = "select * from [Sheet1$]"
        rows = command.ExecuteReader()
        print ([rows.GetName(i) for i in range(rows.FieldCount)])
        for  row in rows:
            print([row[i] for i in range(rows.FieldCount)])
        command.Dispose()
        cnxn.Close()
    except:
        print("\n *** failed ***\n")


# odbc to ACCESS .mdb via pythonnet
import clr, os
clr.AddReference("System.Data")
import System.Data.OleDb as ADONET
import System.Data.Odbc as ODBCNET
import System.Data.Common as DATACOM

filename = os.path.join(os.getcwd(), 'test.mdb')
todo = "select * from users"
print("\nusing odbc via pythonnet to read an ACCESS .mdb file:\n\t", filename , "\n\t", todo)

if os.path.exists(filename):
    CNXNSTRING = 'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;READONLY=FALSE' % filename
    cnxn = ODBCNET.OdbcConnection(CNXNSTRING)
    try:
        cnxn.Open()
        command = cnxn.CreateCommand()
        command.CommandText = "select * from users"
        rows = command.ExecuteReader()
        print ([rows.GetName(i) for i in range(rows.FieldCount)])
        for  row in rows:
            print([row[i] for i in range(rows.FieldCount)])
        command.Dispose()
        cnxn.Close()
    except:
        print("\n *** failed ***\n")

# DAO via pythonnet: works ONLY if you have the 32 (or 64 bit) driver.
import clr, os
clr.AddReference("System.Data")
import System.Data.OleDb as ADONET
import System.Data.Odbc as ODBCNET
import System.Data.Common as DATACOM

filename = os.path.join(os.getcwd(), 'test.accdb')
todo = "select * from users"
print("\nusing DAO via pythonnet to read an ACCESS .mdb file:\n\t", filename , "\n\t", todo)
if os.path.exists(filename):
    # needs a driver in 32 or 64 bit like your running python
    # https://www.microsoft.com/download/details.aspx?id=13255
    CNXNSTRING = 'Provider=Microsoft.ACE.OLEDB.12.0; Data Source=%s;READONLY=FALSE' % filename
    cnxn = ADONET.OleDbConnection(CNXNSTRING)
    try:
        cnxn.Open()
        command = cnxn.CreateCommand()
        command.CommandText = todo
        # command.CommandText = 'select id, name from people where group_id = @group_id'
        # command.Parameters.Add(SqlParameter('group_id', 23))
        rows = command.ExecuteReader()
        print ([rows.GetName(i) for i in range(rows.FieldCount)])
        for  row in rows:
            print([row[i] for i in range(rows.FieldCount)])
        command.Dispose()
        cnxn.Close()
    except:
        print("\n *** failed ***\n")
