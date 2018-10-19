# -*- coding: utf-8 -*-

from MzSTools.constants import *
import os, shutil, sqlite3, csv
from qgis.core import QgsVectorLayer, QgsFeatureRequest, QgsField, QgsVectorJoinInfo, QgsExpressionContext, QgsExpressionContextScope
from qgis.utils import QgsExpression

from abstract_worker import AbstractWorker, UserAbortedNotification


class ImportWorker(AbstractWorker):
    '''Worker class handling data import from existing project'''

    def __init__(self, proj_abs_path, in_dir, tab_dir, map_registry_instance):
        AbstractWorker.__init__(self)
#         self.steps = steps
        self.proj_abs_path = proj_abs_path
        self.in_dir = in_dir
        self.tab_dir = tab_dir
        self.map_registry_instance = map_registry_instance

        self.current_step = 1
        self.check_sito_p = True
        self.check_sito_l = True

    def work(self):
        path_tabelle = self.proj_abs_path + os.sep + "allegati" + os.sep + "altro"
        z_list = []

        # calculate steps
        total_steps = len(POSIZIONE) + 5

        # step 1 (preparing data)
        ###############################################
        self.set_message.emit('Creating folders...')

        if os.path.exists(path_tabelle + os.sep + "Indagini"):
            shutil.rmtree(path_tabelle + os.sep + "Indagini")

        os.makedirs(path_tabelle + os.sep + "Indagini")
        self.copy_files(self.in_dir + os.sep + "Indagini", path_tabelle + os.sep + "Indagini")

        for nome_tab in LISTA_TAB:
            if os.path.exists(path_tabelle + os.sep + nome_tab):
                os.remove(path_tabelle + os.sep + nome_tab)

        self.set_log_message.emit('Folder structure -> OK\n')

        self.set_message.emit('Copying tables...')
        self.copy_files(self.tab_dir, path_tabelle)

        # end step 1
        if self.killed:
            raise UserAbortedNotification('USER Killed')
        self.current_step = self.current_step + 1
        self.progress.emit(self.current_step * 100/total_steps)

        self.set_log_message.emit('Tables copy -> OK\n')

        # step 2 (inserting features)
        ###############################################
        for chiave, valore in POSIZIONE.iteritems():
            
            if not os.path.exists(self.in_dir + os.sep + valore[0] + os.sep + valore[1] + ".shp"):
                self.set_log_message.emit("  '" + chiave + "' shapefile does not exist!\n")
                continue
            
            sourceLYR = QgsVectorLayer(self.in_dir + os.sep + valore[0] + os.sep + valore[1] + ".shp", valore[1], 'ogr')
            destLYR = self.map_registry_instance.mapLayersByName(chiave)[0]
#             dest_field = []
#             for x in destLYR.fields():
#                 dest_field.append(x)

            commonFields = self.attribute_adaptor(destLYR,sourceLYR)

            if chiave == "Siti puntuali":
                if os.path.exists(path_tabelle + os.sep + 'Sito_Puntuale.txt'):
#                     self.calc_siti(path_tabelle, "Ind_pu", 'Sito_Puntuale.txt', "csv_spu", 'ID_SPU', DIZIO_CAMPI_P, 'Siti puntuali', 'id_spu')
                    self.insert_siti(sourceLYR, path_tabelle + os.sep + 'Sito_Puntuale.txt', "puntuale")
                    self.set_message.emit("  '" + chiave + "' shapefile has been copied!")
                    self.set_log_message.emit("  '" + chiave + "' shapefile has been copied!\n")
                    z_list.append("Sito_Puntuale")
                else:
                    self.set_log_message.emit("  Table 'Sito_Puntuale.txt' does not exist!\n")
                    self.check_sito_p = False

            elif chiave == "Siti lineari":
                if os.path.exists(path_tabelle + os.sep + 'Sito_Lineare.txt'):
#                     self.calc_siti(path_tabelle, "Ind_ln", 'Sito_Lineare.txt', "csv_sln", 'ID_SLN', DIZIO_CAMPI_L, 'Siti lineari', 'id_sln')
                    self.insert_siti(sourceLYR, path_tabelle + os.sep + 'Sito_Lineare.txt', "lineare")
                    self.set_message.emit("  '" + chiave + "' shapefile has been copied!")
                    self.set_log_message.emit("  '" + chiave + "' shapefile has been copied!\n")
                    z_list.append("Sito_Lineare")
                else:
                    self.set_log_message.emit("  Table 'Sito_Lineare.txt' does not exist!\n")
                    self.check_sito_l = False

            elif chiave == "Zone stabili liv 2" or chiave == "Zone instabili liv 2":
                sourceFeatures = sourceLYR.getFeatures(QgsFeatureRequest(QgsExpression( " \"LIVELLO\" = 2 " )))
                self.calc_layer(sourceFeatures, destLYR, commonFields)
                self.set_message.emit("  '" + chiave + "' shapefile has been copied!")
                self.set_log_message.emit("  '" + chiave + "' shapefile has been copied!\n")
                

            elif chiave == "Zone stabili liv 3" or chiave == "Zone instabili liv 3":
                sourceFeatures = sourceLYR.getFeatures(QgsFeatureRequest(QgsExpression( " \"LIVELLO\" = 3 " )))
                self.calc_layer(sourceFeatures, destLYR, commonFields)
                self.set_message.emit("  '" + chiave + "' shapefile has been copied!")
                self.set_log_message.emit("  '" + chiave + "' shapefile has been copied!\n")

            elif chiave == "Comune del progetto":
                pass
            else:
                sourceFeatures = sourceLYR.getFeatures()
                self.calc_layer(sourceFeatures, destLYR, commonFields)
                self.set_log_message.emit("  '" + chiave + "' shapefile has been copied!\n")
                

            if self.killed:
                break

            self.current_step = self.current_step + 1
            self.progress.emit(self.current_step * 100/total_steps)
        # end for

        if self.killed:
            raise UserAbortedNotification('USER Killed')

        self.set_log_message.emit('Insert features -> OK\n')
        # end inserting features

        # step 3 (inserting indagini puntuali)
        ###############################################
        if self.check_sito_p is True and os.path.exists(path_tabelle + os.sep + "Indagini_Puntuali.txt"):
            self.set_message.emit('Inserting Indagini_Puntuali...')
            z_list.append("Indagini_Puntuali")
            self.insert_table("indagini_puntuali", path_tabelle + os.sep + "Indagini_Puntuali.txt")
            self.set_log_message.emit('Insert Indagini_Puntuali -> OK\n')
            
            if os.path.exists(path_tabelle + os.sep + "Parametri_Puntuali.txt"):
                self.set_message.emit('Inserting Parametri_Puntuali...')
                z_list.append("Parametri_Puntuali")
                self.insert_table("parametri_puntuali", path_tabelle + os.sep + "Parametri_Puntuali.txt")
                self.set_log_message.emit('Insert Parametri_Puntuali -> OK\n')
                
                if os.path.exists(path_tabelle + os.sep + "Curve.txt"):
                    self.set_message.emit('Inserting Curve...')
                    z_list.append("Curve")
                    self.insert_table("curve", path_tabelle + os.sep + "Curve.txt")
                    self.set_log_message.emit('Insert Curve -> OK\n')
        
        '''
        self.set_message.emit('Checking Indagini_Puntuali...')
        path_db = self.proj_abs_path + os.sep + "db" + os.sep + "indagini.sqlite"

        if self.check_sito_p is True and os.path.exists(path_tabelle + os.sep + "Indagini_Puntuali.txt"):
            z_list.append("Indagini_Puntuali")

            i_p = self.map_registry_instance.mapLayersByName('Indagini puntuali')[0]
            field_i_p = QgsField('temp_pkey_spu', QVariant.LongLong)
            i_p.addExpressionField('"id_spu"', field_i_p)
            conn = sqlite3.connect(path_db)
            conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
            cur = conn.cursor()
            csv_file = path_tabelle + os.sep + "Indagini_Puntuali.txt"
            with open(csv_file,'rb') as fin:
                dr = csv.DictReader(fin, delimiter=';', quotechar='"')

#                 to_db = [(i['pkey_indpu'], i['pkey_spu'], i['classe_ind'], i['tipo_ind'], i['ID_INDPU'], i['id_indpuex'], i['arch_ex'], i['note_ind'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['data_ind'], i['doc_pag'], i['doc_ind']) for i in dr]
                to_db = []
                for i in dr:
                    # transform empty strings to None to circumvent db CHECKs
                    for k in i:
                        if i[k] == "":
                            i[k] = None
                    to_db.append((i['pkey_indpu'], i['pkey_spu'], i['classe_ind'], i['tipo_ind'], i['ID_INDPU'], i['id_indpuex'], i['arch_ex'], i['note_ind'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['data_ind'], i['doc_pag'], i['doc_ind']))

            self.set_message.emit('Inserting indagini_puntuali...')
            cur.executemany("INSERT INTO indagini_puntuali (pkuid, id_spu, classe_ind, tipo_ind, id_indpu, id_indpuex, arch_ex, note_ind, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, data_ind, doc_pag, doc_ind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);", to_db)

            i_p.addExpressionField('"id_spu"', field_i_p)
            conn.commit()
            conn.close()

            s_p = self.map_registry_instance.mapLayersByName('Siti puntuali')[0]
            self.calc_join(i_p, s_p, 'temp_pkey_spu', '"Siti puntuali_id_spu"', "id_spu")

            self.set_log_message.emit('Insert Indagini puntuali -> OK\n')

            if os.path.exists(path_tabelle + os.sep + "Parametri_Puntuali.txt"):
                z_list.append("Parametri_Puntuali")

                p_p = self.map_registry_instance.mapLayersByName('Parametri puntuali')[0]
                field_p_p = QgsField('temp_pkey_indpu', QVariant.LongLong)
                p_p.addExpressionField('"id_indpu"', field_p_p)
                conn = sqlite3.connect(path_db)
                conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
                cur = conn.cursor()
                csv_file = path_tabelle + os.sep + "Parametri_Puntuali.txt"
                with open(csv_file,'rb') as fin:
                    dr = csv.DictReader(fin, delimiter=';', quotechar='"')
#                     to_db = [(i['pkey_parpu'], i['pkey_indpu'], i['tipo_parpu'], i['ID_PARPU'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['valore'], i['attend_mis'], i['tab_curve'], i['note_par'], i['data_par']) for i in dr]
                    to_db = []
                    for i in dr:
                        # transform empty strings to None to circumvent db CHECKs
                        for k in i:
                            if i[k] == "":
                                i[k] = None
                        to_db.append((i['pkey_parpu'], i['pkey_indpu'], i['tipo_parpu'], i['ID_PARPU'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['valore'], i['attend_mis'], i['tab_curve'], i['note_par'], i['data_par']))

                self.set_message.emit('Inserting parametri_puntuali...')
                cur.executemany("INSERT INTO parametri_puntuali (pkuid , id_indpu , tipo_parpu , id_parpu , prof_top , prof_bot , spessore , quota_slm_top , quota_slm_bot , valore , attend_mis , tab_curve , note_par , data_par) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?);", to_db)

                p_p.addExpressionField('"id_indpu"', field_p_p)
                conn.commit()
                conn.close()

                i_p = self.map_registry_instance.mapLayersByName('Indagini puntuali')[0]
                self.calc_join(p_p, i_p, 'temp_pkey_indpu', '"Indagini puntuali_id_indpu"', "id_indpu")

                self.set_log_message.emit('Insert Parametri puntuali -> OK\n')

                if os.path.exists(path_tabelle + os.sep + "Curve.txt"):
                    z_list.append("Curve")

                    cu = self.map_registry_instance.mapLayersByName('Curve di riferimento')[0]
                    field_cu = QgsField('temp_pkey_parpu', QVariant.LongLong)
                    cu.addExpressionField('"id_parpu"', field_cu)
                    conn = sqlite3.connect(path_db)
                    conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
                    cur = conn.cursor()
                    csv_file = path_tabelle + os.sep + "Curve.txt"
                    with open(csv_file,'rb') as fin:
                        dr = csv.DictReader(fin, delimiter=';', quotechar='"')
#                         to_db = [(i['pkey_curve'], i['pkey_parpu'], i['cond_curve'], i['varx'], i['vary']) for i in dr]
                        to_db = []
                        for i in dr:
                            # transform empty strings to None to circumvent db CHECKs
                            for k in i:
                                if i[k] == "":
                                    i[k] = None
                            to_db.append((i['pkey_curve'], i['pkey_parpu'], i['cond_curve'], i['varx'], i['vary']))


                    self.set_message.emit('Inserting curve...')
                    cur.executemany("INSERT INTO curve (pkuid, id_parpu, cond_curve, varx, vary) VALUES (?,?,?,?,?);", to_db)

                    cu.addExpressionField('"id_parpu"', field_cu)
                    conn.commit()
                    conn.close()

                    p_p = self.map_registry_instance.mapLayersByName('Parametri puntuali')[0]
                    self.calc_join(cu, p_p, 'temp_pkey_parpu', '"Parametri puntuali_id_parpu"', "id_parpu")

                    self.set_log_message.emit('Insert Curve -> OK\n')
        
        '''
        
        # end inserting indagini puntuali
        if self.killed:
            raise UserAbortedNotification('USER Killed')
        self.current_step = self.current_step + 1
        self.progress.emit(self.current_step * 100/total_steps)

        # step 4 (inserting indagini lineari)
        ###############################################
        if self.check_sito_l is True and os.path.exists(path_tabelle + os.sep + "Indagini_Lineari.txt"):
            self.set_message.emit('Inserting Indagini_Lineari...')
            z_list.append("Indagini_Lineari")
            self.insert_table("indagini_lineari", path_tabelle + os.sep + "Indagini_Lineari.txt")
            self.set_log_message.emit('Insert Indagini_Lineari -> OK\n')
            
            if os.path.exists(path_tabelle + os.sep + "Parametri_Lineari.txt"):
                self.set_message.emit('Inserting Parametri_Lineari...')
                z_list.append("Parametri_Lineari")
                self.insert_table("parametri_lineari", path_tabelle + os.sep + "Parametri_Lineari.txt")
                self.set_log_message.emit('Insert Parametri_Lineari -> OK\n')
        
        
        '''
        self.set_message.emit('Checking Indagini_Lineari...')

        if self.check_sito_l is True and os.path.exists(path_tabelle + os.sep + "Indagini_Lineari.txt"):
            z_list.append("Indagini_Lineari")

            i_l = self.map_registry_instance.mapLayersByName('Indagini lineari')[0]
            field_i_l = QgsField('temp_pkey_sln', QVariant.LongLong)
            i_l.addExpressionField('"id_sln"', field_i_l)
            conn = sqlite3.connect(path_db)
            conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
            cur = conn.cursor()
            csv_file = path_tabelle + os.sep + "Indagini_Lineari.txt"
            with open(csv_file,'rb') as fin:
                dr = csv.DictReader(fin, delimiter=';', quotechar='"')
#                 to_db = [(i['pkey_indln'], i['pkey_sln'], i['classe_ind'], i['tipo_ind'], i['ID_INDLN'], i['id_indlnex'], i['arch_ex'], i['note_indln'], i['data_ind'], i['doc_pag'], i['doc_ind']) for i in dr]
                to_db = []
                for i in dr:
                    # transform empty strings to None to circumvent db CHECKs
                    for k in i:
                        if i[k] == "":
                            i[k] = None
                    to_db.append((i['pkey_indln'], i['pkey_sln'], i['classe_ind'], i['tipo_ind'], i['ID_INDLN'], i['id_indlnex'], i['arch_ex'], i['note_indln'], i['data_ind'], i['doc_pag'], i['doc_ind']))

            self.set_message.emit('Inserting indagini_lineari...')
            cur.executemany("INSERT INTO indagini_lineari (pkuid, id_sln, classe_ind, tipo_ind, id_indln, id_indlnex, arch_ex, note_indln, data_ind, doc_pag, doc_ind) VALUES (?,?,?,?,?,?,?,?,?,?,?);", to_db)

            i_l.addExpressionField('"id_sln"', field_i_l)
            conn.commit()
            conn.close()

            s_l = self.map_registry_instance.mapLayersByName('Siti lineari')[0]
            self.calc_join(i_l, s_l, 'temp_pkey_sln', '"Siti lineari_id_sln"', "id_sln")

            self.set_log_message.emit('Insert Indagini lineari -> OK\n')

            if os.path.exists(path_tabelle + os.sep + "Parametri_Lineari.txt"):
                z_list.append("Parametri_Lineari")

                p_l = self.map_registry_instance.mapLayersByName('Parametri lineari')[0]
                field_p_l = QgsField('temp_pkey_indln', QVariant.LongLong)
                p_l.addExpressionField('"id_indln"', field_p_l)
                conn = sqlite3.connect(path_db)
                conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
                cur = conn.cursor()
                csv_file = path_tabelle + os.sep + "Parametri_Lineari.txt"
                with open(csv_file,'rb') as fin:
                    dr = csv.DictReader(fin, delimiter=';', quotechar='"')
#                     to_db = [(i['pkey_parln'], i['pkey_indln'], i['tipo_parln'], i['ID_PARLN'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['valore'], i['attend_mis'], i['note_par'], i['data_par']) for i in dr]
                    to_db = []
                    for i in dr:
                        # transform empty strings to None to circumvent db CHECKs
                        for k in i:
                            if i[k] == "":
                                i[k] = None
                        to_db.append((i['pkey_parln'], i['pkey_indln'], i['tipo_parln'], i['ID_PARLN'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['valore'], i['attend_mis'], i['note_par'], i['data_par']))

                self.set_message.emit('Inserting parametri_lineari...')
                cur.executemany("INSERT INTO parametri_lineari (pkuid, id_indln, tipo_parln, id_parln, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, valore, attend_mis, note_par, data_par) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?);", to_db)

                p_l.addExpressionField('"id_indln"', field_p_l)
                conn.commit()
                conn.close()

                i_l = self.map_registry_instance.mapLayersByName('Indagini lineari')[0]
                self.calc_join(p_l, i_l, 'temp_pkey_indln', '"Indagini lineari_id_indln"', "id_indln")

                self.set_log_message.emit('Insert Parametri lineari -> OK\n')
        '''
        
        if self.check_sito_p is False:
            self.set_log_message.emit("'Ind_pu' layer and/or 'Sito_Puntuale' table are not present! The correlated surveys and parameters tables will not be copied!\n\n")
        if self.check_sito_l is False:
            self.set_log_message.emit("'Ind_ln' layer and/or 'Sito_Lineare' table are not present! The correlated surveys and parameters tables will not be copied!\n\n")
        if self.check_sito_p is True and self.check_sito_l is True:
            tab_mancanti = list(set(LISTA_TAB) - set(z_list))
            for t_lost in tab_mancanti:
                self.set_log_message.emit("'" + t_lost + "' table does not exist!\n")

        # end inserting indagini lineari
        if self.killed:
            raise UserAbortedNotification('USER Killed')
        self.current_step = self.current_step + 1
        self.progress.emit(self.current_step * 100/total_steps)

        # step 5 (miscellaneous files and cleanup)
        ###############################################
        self.set_message.emit('Adding miscellaneous files...')

        dizio_folder = {"Plot" : ["OLD_Plot", self.proj_abs_path + os.sep + "allegati" + os.sep + "Plot", self.in_dir + os.sep + "Plot"], "Documenti" : ["OLD_Documenti", self.proj_abs_path + os.sep + "allegati" + os.sep + "Documenti", self.in_dir + os.sep + "Indagini" + os.sep + "Documenti"], "Spettri" : ["OLD_Spettri", self.proj_abs_path + os.sep + "allegati" + os.sep + "Spettri", self.in_dir + os.sep + "MS23" + os.sep + "Spettri"]}

        for chiave_fold, valore_fold in dizio_folder.iteritems():
            self.set_message.emit("Copying '" + chiave_fold + "' folder")
            if os.path.exists(valore_fold[2]):
                if os.path.exists(self.proj_abs_path + os.sep + "allegati" + os.sep + chiave_fold):
                    shutil.rmtree(self.proj_abs_path + os.sep + "allegati" + os.sep + chiave_fold)
                    shutil.copytree(valore_fold[2], valore_fold[1])
                else:
                    shutil.copytree(self.in_dir + os.sep + chiave_fold, self.proj_abs_path + os.sep + "allegati" + os.sep + chiave_fold)
                self.set_log_message.emit('Folder ' + chiave_fold + ' copy -> OK\n')
            else:
                self.set_log_message.emit(chiave_fold + " does not exist!")

            if self.killed:
                break

        self.set_message.emit('Final cleanup...')
        shutil.rmtree(self.proj_abs_path + os.sep + "allegati" + os.sep + "altro")
        os.makedirs(self.proj_abs_path + os.sep + "allegati" + os.sep + "altro")

        # end miscellaneous files and cleanup
        if self.killed:
            raise UserAbortedNotification('USER Killed')
        self.current_step = self.current_step + 1
        self.progress.emit(self.current_step * 100/total_steps)

        return 'Import completed!'

    def attribute_adaptor(self, targetLayer, sourceLayer):
        targetLayerFields = []
        sourceLayerFields = []
        primaryKeyList = []

        for index in targetLayer.dataProvider().pkAttributeIndexes():
            primaryKeyList.append(targetLayer.dataProvider().fields().at(index).name())

        for field in sourceLayer.dataProvider().fields().toList():
            sourceLayerFields.append(field.name())

        for field in targetLayer.dataProvider().fields().toList():
            targetLayerFields.append(field.name())

        commonFields = list(set(sourceLayerFields) & set(targetLayerFields))
        commonFields = list(set(commonFields)-set(primaryKeyList))

        return commonFields

    def attribute_fill(self, qgsFeature, targetLayer, commonFields):

        featureFields = {}

        for field in qgsFeature.fields().toList():
            if field.name() == "desc_modco":
                featureFields["desc_modcoord"] = qgsFeature[field.name()]
            elif field.name() == "mod_identc":
                featureFields["mod_identcoord"] = qgsFeature[field.name()]
            elif field.name() == "ub_prov":
                featureFields["ubicazione_prov"] = qgsFeature[field.name()]
            elif field.name() == "ub_com":
                featureFields["ubicazione_com"] = qgsFeature[field.name()]
            elif field.name() == "ID_SPU":
                featureFields["id_spu"] = qgsFeature[field.name()]
            elif field.name() == "ID_SLN":
                featureFields["id_sln"] = qgsFeature[field.name()]
            else:
                featureFields[field.name()] = qgsFeature[field.name()]

        qgsFeature.setFields(targetLayer.dataProvider().fields())
        if commonFields:
            for fieldName in commonFields:
                qgsFeature[fieldName]=featureFields[fieldName]

        return qgsFeature

    def calc_layer(self, sourceFeatures, destLYR, commonFields):

        featureList = []
        for feature in sourceFeatures:
            geom = feature.geometry()
            if geom:
                err = geom.validateGeometry()
                if not err:
                    modifiedFeature = self.attribute_fill(feature,destLYR,commonFields)
                    featureList.append(modifiedFeature)
                else:
                    self.set_log_message.emit("  Geometry error (feature %d will not be copied)\n" % (feature.id()+1))

        data_provider = destLYR.dataProvider()
        current_feature = 1
        for f in featureList:
            self.set_message.emit(destLYR.name() + ": inserting feature " + str(current_feature) + "/" + str(len(featureList)))
            data_provider.addFeatures([f])
            current_feature = current_feature + 1
            if self.killed:
                break

        if self.killed:
            raise UserAbortedNotification('USER Killed')

    def insert_siti(self, vector_layer, txt_table, sito_type):
        '''
        QGIS TEST:
        import csv, sqlite3, chardet
        def insert_siti(vector_layer, txt_table):
            dict_sito = {}
            conn = sqlite3.connect(r"C:\Users\Francesco\Documents\044034_Montedinove\db\indagini.sqlite")
            conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
            conn.enable_load_extension(True)
            try:
                conn.execute('SELECT load_extension("mod_spatialite")')
                conn.execute('DELETE FROM sito_puntuale')
                cur = conn.cursor()
                with open(txt_table,'r') as table:
                    dr = csv.DictReader(table, delimiter=';', quotechar='"')
                    for i in dr:
                        for key in i.keys():
                            dict_sito[key] = i[key]
                            if key == "ID_SPU":
                                for feature in vector_layer.getFeatures():
                                    if feature["ID_SPU"] == dict_sito["ID_SPU"]:
                                        geom = feature.geometry().exportToWkt()
                        cur.execute("INSERT INTO sito_puntuale (id_spu, geom) VALUES ('"  + i[key] + "', GeomFromText('" + geom + "', 32633));")
                        lastid = cur.lastrowid
                        print dict_sito.keys()
                        cur.execute('UPDATE sito_puntuale SET pkuid = ?, indirizzo = ?, mod_identcoord = ?,
                                            desc_modcoord = ?, quota_slm = ?, modo_quota = ?, data_sito = ?, note_sito = ? 
                                            WHERE pkuid = ?;',  (dict_sito["pkey_spu"], dict_sito["indirizzo"], dict_sito["mod_identcoord"],
                                            dict_sito["desc_modcoord"], dict_sito["quota_slm"], dict_sito["modo_quota"],
                                            dict_sito["data_sito"], dict_sito["note_sito"], lastid))
                                                    
                conn.commit()
            finally:
                conn.close()
        
        shp_path = r"C:\Users\Francesco\Documents\montedinove\44034_Montedinove\Indagini\Ind_pu.shp"
        layer = QgsVectorLayer(shp_path, '', 'ogr')
        txt_path = r"C:\Users\Francesco\Documents\montedinove\tab_montedinove\Sito_Puntuale.txt"
        insert_siti(layer, txt_path)
        '''
        
        ins_data_s_point = """
            CREATE TRIGGER ins_data_s_point 
            AFTER INSERT ON sito_puntuale 
            FOR EACH ROW 
            BEGIN 
            UPDATE sito_puntuale 
            SET ubicazione_com = ( 
            SELECT comuni.cod_com 
            FROM sito_puntuale, comuni 
            WHERE pkuid = NEW.pkuid AND 
            intersects(sito_puntuale.geom, comuni.Geometry) 
            ) 
            WHERE pkuid = NEW.pkuid; 
            UPDATE sito_puntuale 
            SET ubicazione_prov = ( 
            SELECT comuni.cod_prov 
            FROM sito_puntuale, comuni 
            WHERE pkuid = NEW.pkuid AND 
            intersects(sito_puntuale.geom, comuni.Geometry) 
            ) 
            WHERE pkuid = NEW.pkuid; 
            UPDATE sito_puntuale 
            SET id_spu = ubicazione_prov || ubicazione_com || 'P' || pkuid; 
            UPDATE sito_puntuale 
            SET coord_x = ( 
            SELECT round(X(geom)) 
            FROM sito_puntuale 
            WHERE pkuid = NEW.pkuid 
            ) 
            WHERE pkuid = NEW.pkuid; 
            UPDATE sito_puntuale 
            SET coord_y = ( 
            SELECT round(Y(geom)) 
            FROM sito_puntuale 
            WHERE pkuid = NEW.pkuid 
            ) 
            WHERE pkuid = NEW.pkuid; 
            END
        """
        
        ins_data_s_line = """
            CREATE TRIGGER ins_data_s_line 
            AFTER INSERT ON sito_lineare 
            FOR EACH ROW 
            BEGIN 
            UPDATE sito_lineare 
            SET ubicazione_com = ( 
            SELECT comuni.cod_com 
            FROM sito_lineare, comuni 
            WHERE pkuid = NEW.pkuid AND 
            intersects(sito_lineare.geom, comuni.Geometry) 
            ) 
            WHERE pkuid = NEW.pkuid; 
            UPDATE sito_lineare 
            SET ubicazione_prov = ( 
            SELECT comuni.cod_prov 
            FROM sito_lineare, comuni 
            WHERE pkuid = NEW.pkuid AND 
            intersects(sito_lineare.geom, comuni.Geometry) 
            ) 
            WHERE pkuid = NEW.pkuid; 
            UPDATE sito_lineare 
            SET id_sln = ubicazione_prov || ubicazione_com || 'L' || pkuid; 
            UPDATE sito_lineare 
            SET acoord_x = ( 
            SELECT round(X(StartPoint(geom))) 
            FROM sito_lineare 
            WHERE pkuid = NEW.pkuid 
            ) 
            WHERE pkuid = NEW.pkuid; 
            UPDATE sito_lineare 
            SET acoord_y = ( 
            SELECT round(Y(StartPoint(geom))) 
            FROM sito_lineare 
            WHERE pkuid = NEW.pkuid 
            ) 
            WHERE pkuid = NEW.pkuid; 
            UPDATE sito_lineare 
            SET bcoord_x = ( 
            SELECT round(X(EndPoint(geom))) 
            FROM sito_lineare 
            WHERE pkuid = NEW.pkuid 
            ) 
            WHERE pkuid = NEW.pkuid; 
            UPDATE sito_lineare 
            SET bcoord_y = ( 
            SELECT round(Y(EndPoint(geom))) 
            FROM sito_lineare 
            WHERE pkuid = NEW.pkuid 
            ) 
            WHERE pkuid = NEW.pkuid; 
            END
        """
        
        if sito_type == "puntuale":
            id_field_name = "ID_SPU"
            tab_name = "sito_puntuale"
        else:
            id_field_name = "ID_SLN"
            tab_name = "sito_lineare"
        path_db = self.proj_abs_path + os.sep + "db" + os.sep + "indagini.sqlite"
        dict_sito = {}
        conn = sqlite3.connect(path_db)
        conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
        conn.enable_load_extension(True)
        try:
            conn.execute('SELECT load_extension("mod_spatialite")')
            cur = conn.cursor()
            with open(txt_table,'r') as table:
                dr = csv.DictReader(table, delimiter=';', quotechar='"')
                current_feature = 1
                row_num = len(list(dr))
                    
                table.seek(0)
                next(dr)
                for i in dr:
                    self.set_message.emit("Sito %s: inserting feature %s/%s" % (sito_type, str(current_feature), str(row_num)))
                    for key in i.keys():
                        dict_sito[key] = i[key]
                        if key == id_field_name:
                            for feature in vector_layer.getFeatures():
                                if feature[id_field_name] == dict_sito[id_field_name]:
                                    geom = feature.geometry().exportToWkt()
                    if sito_type == "puntuale":
                        # drop insert trigger to speed up import process
                        # cur.execute("DROP TRIGGER ins_data_s_point")
                        
                        cur.execute("INSERT INTO sito_puntuale (id_spu, geom) VALUES ('"  + dict_sito["ID_SPU"] + "', GeomFromText('" + geom + "', 32633));")
                        lastid = cur.lastrowid
                        
                        # restore trigger ins_data_s_point 
                        # cur.execute(ins_data_s_point)
                        
                        cur.execute('''UPDATE sito_puntuale SET pkuid = ?, indirizzo = ?, mod_identcoord = ?,
                            desc_modcoord = ?, quota_slm = ?, modo_quota = ?, data_sito = ?, note_sito = ? 
                            WHERE pkuid = ?;''',  (dict_sito["pkey_spu"], dict_sito["indirizzo"], dict_sito["mod_identcoord"],
                            dict_sito["desc_modcoord"], dict_sito["quota_slm"], dict_sito["modo_quota"],
                            dict_sito["data_sito"], dict_sito["note_sito"], lastid))
                    else:
                        # drop insert trigger to speed up import process
                        # cur.execute("DROP TRIGGER ins_data_s_line")
                        
                        cur.execute("INSERT INTO sito_lineare (id_sln, geom) VALUES ('"  + dict_sito["ID_SLN"] + "', GeomFromText('" + geom + "', 32633));")
                        lastid = cur.lastrowid
                        
                        # restore trigger ins_data_s_line 
                        # cur.execute(ins_data_s_line)
                        
                        cur.execute('''UPDATE sito_lineare SET pkuid = ?, mod_identcoord = ?,
                            desc_modcoord = ?, aquota = ?, bquota = ?, data_sito = ?, note_sito = ? 
                            WHERE pkuid = ?;''',  (dict_sito["pkey_sln"], dict_sito["mod_identcoord"],
                            dict_sito["desc_modcoord"], dict_sito["Aquota"], dict_sito["Bquota"],
                            dict_sito["data_sito"], dict_sito["note_sito"], lastid))
                    
                    current_feature = current_feature + 1
                    if self.killed:
                        break
            
            conn.commit()
            # cur.execute('ANALYZE ' + tab_name)
            # cur.execute('VACUUM')
            cur.execute('SELECT RecoverSpatialIndex()')
        finally:
            conn.close()
     
     
    def insert_table(self, db_table, txt_table):
        
        # indagini_puntuali
        insert_indpu = """
            INSERT INTO indagini_puntuali 
                (pkuid, id_spu, classe_ind, tipo_ind, id_indpu, 
                id_indpuex, arch_ex, note_ind, prof_top, prof_bot, 
                spessore, quota_slm_top, quota_slm_bot, data_ind, 
                doc_pag, doc_ind)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        select_id_spu = "SELECT pkuid, id_spu FROM sito_puntuale WHERE pkuid = ?"
        update_indpu_fkey = "UPDATE indagini_puntuali SET id_spu = ? WHERE pkuid = ?"
        
        # parametri_puntuali
        insert_parpu = """
            INSERT INTO parametri_puntuali 
                (pkuid, id_indpu, tipo_parpu, id_parpu, prof_top, prof_bot, 
                spessore, quota_slm_top, quota_slm_bot, valore, attend_mis, 
                tab_curve, note_par, data_par) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        select_id_indpu = "SELECT pkuid, id_indpu FROM indagini_puntuali WHERE pkuid = ?"
        update_parpu_fkey = "UPDATE parametri_puntuali SET id_indpu = ? WHERE pkuid = ?"
        
        # curve
        insert_curve = """
            INSERT INTO curve (pkuid, id_parpu, cond_curve, varx, vary) 
                VALUES (?,?,?,?,?);"""
        select_id_parpu = "SELECT pkuid, id_parpu FROM parametri_puntuali WHERE pkuid = ?"
        update_curve_fkey = "UPDATE curve SET id_parpu = ? WHERE pkuid = ?"
        
        # indagini_lineari
        insert_indln = """
            INSERT INTO indagini_lineari 
                (pkuid, id_sln, classe_ind, tipo_ind, id_indln, id_indlnex, 
                arch_ex, note_indln, data_ind, doc_pag, doc_ind) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?)"""
        select_id_sln = "SELECT pkuid, id_sln FROM sito_lineare WHERE pkuid = ?"
        update_indln_fkey = "UPDATE indagini_lineari SET id_sln = ? WHERE pkuid = ?"
        
        # parametri_lineari
        insert_parln = """
            INSERT INTO parametri_lineari 
                (pkuid, id_indln, tipo_parln, id_parln, prof_top, prof_bot, 
                spessore, quota_slm_top, quota_slm_bot, valore, attend_mis, 
                note_par, data_par) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        select_id_indln = "SELECT pkuid, id_indln FROM indagini_lineari WHERE pkuid = ?"
        update_parln_fkey = "UPDATE parametri_lineari SET id_indln = ? WHERE pkuid = ?"
        
        path_db = self.proj_abs_path + os.sep + "db" + os.sep + "indagini.sqlite"
        conn = sqlite3.connect(path_db)
        conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
        try:
            cur = conn.cursor()
            with open(txt_table,'r') as table:
                dr = csv.DictReader(table, delimiter=';', quotechar='"')
                for i in dr:
                    # transform empty strings to None to circumvent db CHECKs
                    for k in i:
                        if i[k] == "":
                            i[k] = None
                    if db_table == "indagini_puntuali":
                        to_db = (i['pkey_indpu'], i['pkey_spu'], i['classe_ind'], i['tipo_ind'], i['ID_INDPU'], i['id_indpuex'], i['arch_ex'], i['note_ind'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['data_ind'], i['doc_pag'], i['doc_ind'])
                        fkey = i['pkey_spu']
                        insert_sql = insert_indpu
                        select_parent_sql = select_id_spu
                        update_sql = update_indpu_fkey
                    elif db_table == "parametri_puntuali":
                        to_db = (i['pkey_parpu'], i['pkey_indpu'], i['tipo_parpu'], i['ID_PARPU'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['valore'], i['attend_mis'], i['tab_curve'], i['note_par'], i['data_par'])
                        fkey = i['pkey_indpu']
                        insert_sql = insert_parpu
                        select_parent_sql = select_id_indpu
                        update_sql = update_parpu_fkey
                    elif db_table == "curve":
                        to_db = (i['pkey_curve'], i['pkey_parpu'], i['cond_curve'], i['varx'], i['vary'])
                        fkey = i['pkey_parpu']
                        insert_sql = insert_curve
                        select_parent_sql = select_id_parpu
                        update_sql = update_curve_fkey
                    elif db_table == "indagini_lineari":
                        to_db = (i['pkey_indln'], i['pkey_sln'], i['classe_ind'], i['tipo_ind'], i['ID_INDLN'], i['id_indlnex'], i['arch_ex'], i['note_indln'], i['data_ind'], i['doc_pag'], i['doc_ind'])
                        fkey = i['pkey_sln']
                        insert_sql = insert_indln
                        select_parent_sql = select_id_sln
                        update_sql = update_indln_fkey
                    elif db_table == "parametri_lineari":
                        to_db = (i['pkey_parln'], i['pkey_indln'], i['tipo_parln'], i['ID_PARLN'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['valore'], i['attend_mis'], i['note_par'], i['data_par'])
                        fkey = i['pkey_indln']
                        insert_sql = insert_parln
                        select_parent_sql = select_id_indln
                        update_sql = update_parln_fkey
                    
                    cur.execute(insert_sql, to_db)
                    id_last_insert = cur.lastrowid
                    cur.execute(select_parent_sql, (fkey))
                    id_parent = cur.fetchone()[1]
                    cur.execute(update_sql, (id_parent, id_last_insert))
    
            conn.commit()
        finally:
            conn.close()

    def calc_siti(self, path_tabelle, nome_shape, csv_path, csv_tab_name, id_field, dizionario, nome_layer, id_orig_field):

        shp_path = path_tabelle + os.sep + "Indagini" + os.sep + nome_shape + ".shp"
        fullname = os.path.join(path_tabelle, csv_path).replace('\\', '/')
        shp_layer = QgsVectorLayer(shp_path, '', 'ogr')
        s_geom = self.map_registry_instance.addMapLayer(shp_layer)
        csv_uri = 'file:///%s?delimiter=;' % (fullname)
        s_attr = QgsVectorLayer(csv_uri, csv_tab_name, "delimitedtext")
        self.map_registry_instance.addMapLayer(s_attr)

        joinObject = QgsVectorJoinInfo()
        joinObject.joinLayerId = s_attr.id()
        joinObject.joinFieldName = id_field
        joinObject.targetFieldName = id_field
        joinObject.memoryCache = True
        s_geom.addJoin(joinObject)

        for chiave, valore in dizionario.iteritems():
            s_geom.dataProvider().addAttributes([QgsField(chiave, valore[0])])
            s_geom.updateFields()
            expression = QgsExpression(valore[1])
            expression.prepare(s_geom.pendingFields())
#             s_geom.startEditing()
            for feature in s_geom.getFeatures():
                value = expression.evaluate(feature)
##                feature[chiave] = value
                s_geom.dataProvider().changeAttributeValues({ feature.id() : {s_geom.dataProvider().fieldNameMap()[chiave] : value } })
#                 s_geom.updateFeature(feature)
#             s_geom.commitChanges()

        s = self.map_registry_instance.mapLayersByName(nome_layer)[0]
#         s_geom = self.map_registry_instance.mapLayersByName(nome_shape)[0]
        featureList = []
        commonFields = self.attribute_adaptor(s,s_geom)
        commonFields.append('pkuid')
        commonFields.append('desc_modcoord')
        commonFields.append('mod_identcoord')
        commonFields.append('ubicazione_prov')
        commonFields.append('ubicazione_com')
        commonFields.append(id_orig_field)
        sourceFeatures = s_geom.getFeatures()
        for feature in sourceFeatures:
            geom = feature.geometry()
            if geom:
                err = geom.validateGeometry()
                if not err:
                    modifiedFeature = self.attribute_fill(feature,s,commonFields)
                    featureList.append(modifiedFeature)
                else:
                    self.set_log_message.emit("  Geometry error (feature %d will not be copied)\n" % (feature.id()+1))

        data_provider = s.dataProvider()

        current_feature = 1
        for f in featureList:
            self.set_message.emit(nome_layer + ": inserting feature " + str(current_feature) + "/" + str(len(featureList)))
            data_provider.addFeatures([f])
            current_feature = current_feature + 1
            if self.killed:
                break

        s_geom.removeJoin(s_attr.id())
        self.map_registry_instance.removeMapLayer(s_attr.id())
        self.map_registry_instance.removeMapLayer(s_geom.id())

        if self.killed:
            raise UserAbortedNotification('USER Killed')


    def calc_join(self, orig_tab, link_tab, temp_field, link_field, orig_field):

        path_db = self.proj_abs_path + os.sep + "db" + os.sep + "indagini.sqlite"

        joinObject = QgsVectorJoinInfo()
        joinObject.joinLayerId = link_tab.id()
        joinObject.joinFieldName = 'pkuid'
        joinObject.targetFieldName = temp_field
        joinObject.memoryCache = True
        orig_tab.addJoin(joinObject)

        context = QgsExpressionContext()
        scope = QgsExpressionContextScope()
        context.appendScope(scope)

        expression = QgsExpression(link_field)
        expression.prepare(orig_tab.pendingFields())

        try:
            conn = sqlite3.connect(path_db)
            conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
            cur = conn.cursor()

            for feature in orig_tab.getFeatures():
                scope.setFeature(feature)
                value = expression.evaluate(context)
##                feature[orig_field] = value
                if value is None:
                    pass
                else:
                    nome_tab = LAYER_DB_TAB[orig_tab.name()]
##                    self.set_log_message.emit(nome_tab + "\n")
##                    self.set_log_message.emit(orig_field + "\n")
##                    self.set_log_message.emit(value + "\n")
##                    self.set_log_message.emit(str(feature['pkuid']))
                    cur.execute("UPDATE %s SET %s  = %s WHERE pkuid = %s;" % nome_tab, orig_field, value, str(feature['pkuid']))

            conn.commit()
        except Exception as ex:
            # error will be forwarded upstream
            raise ex
        finally:
            conn.close()

        orig_tab.removeJoin(link_tab.id())

    def copy_files(self, src, dest):
        for file_name in os.listdir(src):
            full_file_name = os.path.join(src, file_name)
            if (os.path.isfile(full_file_name)):
                shutil.copy(full_file_name, dest)

