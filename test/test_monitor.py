import unittest
from types import SimpleNamespace
from deploy.scripts.monitor import failures, poll, send
from unittest.mock import patch, MagicMock


class MonitorTest(unittest.TestCase):
    def test_jobs_may_be_inactive_after_success_but_timers_must_be_active(self):
        checks=[dict(unit='test.service',kind='job',label='Backup')]
        run=lambda *args,**kwargs:SimpleNamespace(stdout='LoadState=loaded\nActiveState=inactive\nResult=success\n')
        self.assertEqual(failures(checks,run),[])
        checks[0]['kind']='timer'
        self.assertEqual(failures(checks,run),['Backup: nicht aktiv'])

    def test_alerts_are_throttled_and_recovery_sent_once(self):
        sent=[];config={'label':'App','checks':[]};deliver=lambda *args:sent.append(args)
        state,action=poll(config,{},now=100000,inspect=lambda _:['Backup: Prüfung fehlgeschlagen'],deliver=deliver)
        self.assertEqual(action,'failure')
        state,action=poll(config,state,now=100001,inspect=lambda _:state['issues'],deliver=deliver)
        self.assertIsNone(action);self.assertEqual(len(sent),1)
        state,action=poll(config,state,now=121600,inspect=lambda _:state['issues'],deliver=deliver)
        self.assertEqual(action,'failure');self.assertEqual(len(sent),2)
        state,action=poll(config,state,now=121601,inspect=lambda _:[],deliver=deliver)
        self.assertEqual(action,'recovery')
        _,action=poll(config,state,now=121602,inspect=lambda _:[],deliver=deliver)
        self.assertIsNone(action);self.assertEqual(len(sent),3)

    def test_delivery_failure_does_not_acknowledge_alert(self):
        state={'issues':[],'sent':0}
        def failed(*args):raise RuntimeError('synthetic SMTP error')
        with self.assertRaises(RuntimeError):
            poll({'label':'App','checks':[]},state,inspect=lambda _:['Backup: nicht aktiv'],deliver=failed)
        self.assertEqual(state,{'issues':[],'sent':0})

    def test_tls_is_mandatory_and_rejected_recipient_is_failure(self):
        smtp=MagicMock();smtp.send_message.return_value={'synthetic@example.invalid':(550,b'rejected')}
        with patch('deploy.scripts.monitor.smtplib.SMTP') as constructor:
            constructor.return_value.__enter__.return_value=smtp
            with self.assertRaises(RuntimeError):
                send({'smtp_user':'sender@example.invalid','smtp_password':'synthetic','recipient':'synthetic@example.invalid'},'Test','No user data')
            smtp.starttls.assert_called_once()
            self.assertEqual([call[0] for call in smtp.method_calls],['ehlo','starttls','ehlo','login','send_message'])

    def test_changed_problem_alerts_immediately_and_public_probe_failure_is_generic(self):
        sent=[]
        config={'label':'Auth','checks':[],'probe_url':'https://auth.myna-ai.ch/.well-known/openid-configuration'}
        state={'issues':['Backup: nicht aktiv'],'sent':100000}
        updated,action=poll(config,state,now=100001,inspect=lambda _:[],probe=lambda _:False,deliver=lambda *args:sent.append(args))
        self.assertEqual(action,'failure')
        self.assertEqual(updated['issues'],['Öffentlicher Zugang: nicht erreichbar'])
        self.assertNotIn('openid-configuration',sent[0][2])

    def test_failed_job_and_missing_unit_are_reported_without_raw_output(self):
        checks=[dict(unit='synthetic.service',kind='job',label='Backup')]
        run=lambda *args,**kwargs:SimpleNamespace(stdout='LoadState=loaded\nActiveState=failed\nResult=exit-code\n')
        self.assertEqual(failures(checks,run),['Backup: Prüfung fehlgeschlagen'])
        run=lambda *args,**kwargs:SimpleNamespace(stdout='LoadState=not-found\nActiveState=inactive\n')
        self.assertEqual(failures(checks,run),['Backup: nicht geladen'])
